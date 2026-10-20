"""
power_db.py — PZEM-017 DC Power Monitoring & Cleaning Efficiency Tracking
==========================================================================
Đọc dữ liệu công suất DC trực tiếp từ PZEM-017 qua USB (Modbus RTU),
lưu vào SQLite, tính hiệu suất vệ sinh trước/sau.

PZEM-017 đo: Voltage (V), Current (A), Power (W), Energy (Wh)
Kết nối: USB → RS485/TTL adapter → PZEM-017
Giao thức: Modbus RTU, slave addr 0x01, baud 9600, 8N2
"""

import os
import sys
import time
import threading
import sqlite3
from datetime import datetime, timedelta
from collections import deque

def _configure_console_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_configure_console_encoding()

# Import minimalmodbus (cho PZEM-017 Modbus RTU)
try:
    import minimalmodbus
    import serial
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    try:
        print("[WARN] minimalmodbus chưa cài — chạy: pip install minimalmodbus")
    except Exception:
        pass


# ── Helper: resolve runtime path ──
def _runtime_path(*parts):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)


# ==================== SQLITE DATABASE ====================

DB_PATH = _runtime_path('solar_power.db')

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS power_readings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    voltage     REAL DEFAULT 0,
    current     REAL DEFAULT 0,
    power       REAL DEFAULT 0,
    energy      REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cleaning_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time        TEXT,
    end_time          TEXT,
    trigger_reason    TEXT,
    dirty_ratio       REAL DEFAULT 0,
    pre_clean_power   REAL DEFAULT 0,
    post_clean_power  REAL DEFAULT 0,
    power_gain        REAL DEFAULT 0,
    improvement_pct   REAL DEFAULT 0,
    ai_label          TEXT,
    ai_confidence     REAL DEFAULT 0,
    snapshot_file     TEXT
);

CREATE TABLE IF NOT EXISTS daily_stats (
    date            TEXT PRIMARY KEY,
    total_energy    REAL DEFAULT 0,
    peak_power      REAL DEFAULT 0,
    avg_power       REAL DEFAULT 0,
    cleaning_count  INTEGER DEFAULT 0,
    avg_improvement REAL DEFAULT 0,
    reading_count   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_power_ts ON power_readings(timestamp);
CREATE INDEX IF NOT EXISTS idx_clean_start ON cleaning_events(start_time);
"""


def get_db():
    """Tạo connection + khởi tạo schema nếu chưa có."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_CREATE_SQL)
    # Auto-migrate new columns for closed-loop support
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cleaning_events)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        new_cols = [
            ("post_dirty_ratio", "REAL DEFAULT 0"),
            ("retries_used", "INTEGER DEFAULT 1"),
            ("post_snapshot_file", "TEXT DEFAULT ''"),
            ("cycle_status", "TEXT DEFAULT 'SUCCESS'"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE cleaning_events ADD COLUMN {col_name} {col_type}")
    except Exception:
        pass
    return conn


def insert_power_reading(voltage, current, power, energy):
    """Lưu 1 bản ghi công suất."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO power_readings (timestamp, voltage, current, power, energy) "
                "VALUES (?, ?, ?, ?, ?)",
                (ts, voltage, current, power, energy)
            )
    except Exception as e:
        print(f"[ERROR] DB insert power error: {e}")


def get_power_history(hours=1):
    """Lấy lịch sử power_readings trong N giờ gần nhất."""
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT timestamp, voltage, current, power, energy "
                "FROM power_readings WHERE timestamp >= ? ORDER BY timestamp",
                (cutoff,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] DB query power history error: {e}")
        return []


def insert_cleaning_event(event_dict):
    """Lưu 1 sự kiện vệ sinh, hỗ trợ đầy đủ các trường chu trình khép kín."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(cleaning_events)")
            cols = {row[1] for row in cursor.fetchall()}

            base_fields = ['start_time', 'end_time', 'trigger_reason', 'dirty_ratio',
                           'pre_clean_power', 'post_clean_power', 'power_gain', 'improvement_pct',
                           'ai_label', 'ai_confidence', 'snapshot_file']
            extra_fields = ['post_dirty_ratio', 'retries_used', 'post_snapshot_file', 'cycle_status']
            fields = [f for f in base_fields if f in cols]
            for f in extra_fields:
                if f in cols:
                    fields.append(f)

            placeholders = ', '.join(['?'] * len(fields))
            field_names = ', '.join(fields)
            values = []
            for f in fields:
                val = event_dict.get(f)
                if val is None:
                    if any(num_key in f for num_key in ['ratio', 'power', 'gain', 'pct', 'used', 'confidence']):
                        val = 0
                    else:
                        val = ''
                values.append(val)

            conn.execute(f"INSERT INTO cleaning_events ({field_names}) VALUES ({placeholders})", values)
    except Exception as e:
        print(f"[ERROR] DB insert cleaning event error: {e}")


def get_cleaning_events(limit=20):
    """Lấy danh sách sự kiện vệ sinh gần nhất."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM cleaning_events ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"[ERROR] DB query cleaning events error: {e}")
        return []


def update_daily_stats(date_str=None):
    """Cập nhật thống kê ngày (gọi cuối mỗi lần đọc power)."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt, MAX(power) as peak, AVG(power) as avg_p, "
                "MAX(energy) as max_e, MIN(energy) as min_e "
                "FROM power_readings WHERE timestamp LIKE ?",
                (f"{date_str}%",)
            ).fetchone()

            if row and row['cnt'] > 0:
                daily_energy = (row['max_e'] or 0) - (row['min_e'] or 0)

                # Đếm cleaning events trong ngày
                clean_row = conn.execute(
                    "SELECT COUNT(*) as cnt, AVG(improvement_pct) as avg_imp "
                    "FROM cleaning_events WHERE start_time LIKE ?",
                    (f"{date_str}%",)
                ).fetchone()

                conn.execute(
                    "INSERT OR REPLACE INTO daily_stats "
                    "(date, total_energy, peak_power, avg_power, cleaning_count, "
                    " avg_improvement, reading_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        date_str,
                        round(daily_energy, 3),
                        round(row['peak'] or 0, 1),
                        round(row['avg_p'] or 0, 1),
                        clean_row['cnt'] if clean_row else 0,
                        round(clean_row['avg_imp'] or 0, 1) if clean_row else 0,
                        row['cnt'],
                    )
                )
    except Exception as e:
        print(f"[ERROR] DB update daily stats error: {e}")


def get_daily_stats(days=7):
    """Lấy thống kê N ngày gần nhất (tự động điền 0 cho các ngày thiếu)."""
    daily_map = {}
    for i in range(days):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        daily_map[d] = {
            'date': d,
            'total_energy': 0.0,
            'peak_power': 0.0,
            'avg_power': 0.0,
            'cleaning_count': 0,
            'avg_improvement': 0.0,
            'reading_count': 0
        }
    cutoff = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_stats WHERE date >= ? ORDER BY date",
                (cutoff,)
            ).fetchall()
            for r in rows:
                d = r['date']
                if d in daily_map:
                    daily_map[d] = dict(r)
            return [daily_map[d] for d in sorted(daily_map.keys())]
    except Exception as e:
        print(f"[ERROR] DB query daily stats error: {e}")
        return [daily_map[d] for d in sorted(daily_map.keys())]


def get_hourly_stats(date_str=None):
    """Gom nhóm dữ liệu công suất trung bình theo từng giờ trong ngày (điền 0 cho giờ thiếu)."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    hourly_map = {
        f"{h:02d}": {
            'hour': f"{h:02d}",
            'avg_voltage': 0.0,
            'avg_current': 0.0,
            'avg_power': 0.0,
            'energy': 0.0
        } for h in range(24)
    }
    
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT strftime('%H', timestamp) as hour, "
                "ROUND(AVG(voltage), 2) as avg_voltage, "
                "ROUND(AVG(current), 3) as avg_current, "
                "ROUND(AVG(power), 1) as avg_power, "
                "ROUND(MAX(energy) - MIN(energy), 3) as energy "
                "FROM power_readings "
                "WHERE timestamp LIKE ? "
                "GROUP BY hour "
                "ORDER BY hour",
                (f"{date_str}%",)
            ).fetchall()
            for r in rows:
                h = r['hour']
                if h in hourly_map:
                    hourly_map[h] = dict(r)
            return [hourly_map[f"{h:02d}"] for h in range(24)]
    except Exception as e:
        print(f"[ERROR] DB query hourly stats error: {e}")
        return [hourly_map[f"{h:02d}"] for h in range(24)]


def get_monthly_stats(year_str=None):
    """Gom nhóm dữ liệu năng lượng hàng tháng trong năm từ daily_stats (điền 0 cho tháng thiếu)."""
    if year_str is None:
        year_str = datetime.now().strftime('%Y')
        
    monthly_map = {
        f"{m:02d}": {
            'month': f"{m:02d}",
            'total_energy': 0.0,
            'peak_power': 0.0,
            'avg_power': 0.0,
            'cleaning_count': 0
        } for m in range(1, 13)
    }
    
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT strftime('%m', date) as month, "
                "ROUND(SUM(total_energy), 3) as total_energy, "
                "ROUND(MAX(peak_power), 1) as peak_power, "
                "ROUND(AVG(avg_power), 1) as avg_power, "
                "SUM(cleaning_count) as cleaning_count "
                "FROM daily_stats "
                "WHERE date LIKE ? "
                "GROUP BY month "
                "ORDER BY month",
                (f"{year_str}%",)
            ).fetchall()
            for r in rows:
                m = r['month']
                if m in monthly_map:
                    monthly_map[m] = dict(r)
            return [monthly_map[f"{m:02d}"] for m in range(1, 13)]
    except Exception as e:
        print(f"[ERROR] DB query monthly stats error: {e}")
        return [monthly_map[f"{m:02d}"] for m in range(1, 13)]


def export_readings_to_json(filepath, start_date=None, end_date=None):
    """Xuất lịch sử đo đạc công suất ra file JSON trên đĩa (cho ứng dụng Desktop)."""
    import json
    try:
        query = "SELECT timestamp, voltage, current, power, energy FROM power_readings"
        params = []
        if start_date and end_date:
            query += " WHERE timestamp >= ? AND timestamp <= ?"
            params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
        query += " ORDER BY timestamp DESC"
        
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
            data = [dict(r) for r in rows]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] DB export JSON error: {e}")
        return False


def export_readings_to_csv(filepath, start_date=None, end_date=None):
    """Xuất lịch sử đo đạc công suất ra file CSV trên đĩa (cho ứng dụng Desktop)."""
    import csv
    try:
        query = "SELECT timestamp, voltage, current, power, energy FROM power_readings"
        params = []
        if start_date and end_date:
            query += " WHERE timestamp >= ? AND timestamp <= ?"
            params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
        elif start_date:
            query += " WHERE timestamp >= ?"
            params = [f"{start_date} 00:00:00"]
        query += " ORDER BY timestamp DESC"
        
        with get_db() as conn:
            rows = conn.execute(query, params).fetchall()
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig viết BOM giúp Excel đọc đúng tiếng Việt
                writer = csv.writer(f)
                writer.writerow(['Thoi gian', 'Dien ap (V)', 'Dong dien (A)', 'Cong suat (W)', 'San luong (kWh)'])
                for r in rows:
                    writer.writerow([r['timestamp'], r['voltage'], r['current'], r['power'], r['energy']])
        return True
    except Exception as e:
        print(f"[ERROR] DB export CSV error: {e}")
        return False


def generate_readings_csv_rows(start_date=None, end_date=None):
    """Generator sinh các dòng CSV (cho Web FastAPI StreamingResponse)."""
    query = "SELECT timestamp, voltage, current, power, energy FROM power_readings"
    params = []
    if start_date and end_date:
        query += " WHERE timestamp >= ? AND timestamp <= ?"
        params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
    query += " ORDER BY timestamp DESC"
    
    try:
        # Gửi BOM UTF-8 trước tiên để Excel nhận diện chuẩn tiếng Việt có dấu
        yield '\ufeff'
        yield "Thoi gian,Dien ap (V),Dong dien (A),Cong suat (W),San luong (kWh)\n"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            while True:
                row = cursor.fetchone()
                if not row:
                    break
                yield f"{row['timestamp']},{row['voltage']},{row['current']},{row['power']},{row['energy']}\n"
    except Exception as e:
        print(f"[ERROR] DB CSV generator error: {e}")


# ==================== POWER MONITOR ====================

class PowerMonitor:
    """
    Đọc dữ liệu PZEM-017 DC trực tiếp qua USB (Modbus RTU).
    Kết nối: PZEM-017 → RS485/TTL → USB adapter → PC
    Giao thức: Modbus RTU, 9600 baud, 8N2, slave address 0x01

    Input Registers (function code 0x04):
      0x0000  Voltage     (unit: 0.01V)
      0x0001  Current     (unit: 0.01A)
      0x0002  Power Low   (unit: 0.1W)   ┐ 32-bit
      0x0003  Power High                 ┘
      0x0004  Energy Low  (unit: 1Wh)    ┐ 32-bit
      0x0005  Energy High                ┘
    """

    PZEM_SLAVE_ADDR = 0x01
    PZEM_BAUD = 9600

    def __init__(self, config, port=None):
        self.config = config
        self.port = port or config.get('PZEM_PORT', 'AUTO')
        self.instrument = None

        # Buffer dữ liệu gần nhất
        self.current = {
            'timestamp': '',
            'voltage': 0.0,
            'current': 0.0,
            'power': 0.0,
            'energy': 0.0,
        }

        # Lịch sử trong RAM (1 giờ, mỗi 10s = 360 bản ghi)
        self.history = deque(maxlen=360)

        # Thread control
        self._running = False
        self._thread = None
        self._read_interval = config.get('POWER_READ_INTERVAL', 10)
        self._connected = False
        self._lock = threading.Lock()

    # ── Kết nối ──

    def _create_instrument(self, port_name):
        """Tạo minimalmodbus instrument cho 1 COM port."""
        inst = minimalmodbus.Instrument(port_name, self.PZEM_SLAVE_ADDR)
        inst.serial.baudrate = self.PZEM_BAUD
        inst.serial.bytesize = 8
        inst.serial.parity = serial.PARITY_NONE
        inst.serial.stopbits = 2
        inst.serial.timeout = 1.0
        inst.mode = minimalmodbus.MODE_RTU
        inst.clear_buffers_before_each_transaction = True
        return inst

    def _find_pzem_port(self):
        """Tự động tìm COM port có PZEM-017 (bỏ qua Bluetooth)."""
        import serial.tools.list_ports
        all_ports = list(serial.tools.list_ports.comports())

        # Lọc bỏ Bluetooth ports (treo rất lâu khi thử mở)
        ports = [p for p in all_ports if 'BTHENUM' not in (p.hwid or '').upper()
                 and 'BLUETOOTH' not in (p.description or '').upper()
                 and 'BTH' not in (p.hwid or '').upper()]

        print(f"[POWER] PZEM: Đang quét {len(ports)} cổng COM USB (bỏ qua {len(all_ports)-len(ports)} cổng Bluetooth)...")
        sys.stdout.flush()

        # Ưu tiên các USB serial chips phổ biến
        usb_first = sorted(ports, key=lambda p: 0 if any(
            chip in (p.description or '').upper() or chip in (p.hwid or '').upper()
            for chip in ['CH340', 'CH341', 'FTDI', 'CP210', 'PL2303', 'USB']
        ) else 1)

        for p in usb_first:
            print(f"[SCAN] Thử kết nối PZEM-017 trên {p.device} ({p.description or 'Không có mô tả'})...")
            sys.stdout.flush()
            inst = None
            try:
                inst = self._create_instrument(p.device)
                # Tạm thời giảm timeout xuống 0.5s để quét nhanh hơn
                inst.serial.timeout = 0.5
                
                # Thử đọc register voltage
                v = inst.read_register(0x0000, functioncode=4)
                
                # Trở lại timeout mặc định sau khi quét thành công
                inst.serial.timeout = 1.0
                
                print(f"[OK] Phát hiện PZEM-017 trên {p.device}! Điện áp: {v*0.01:.2f}V")
                sys.stdout.flush()
                return inst
            except Exception as e:
                err_msg = str(e).strip().split('\n')[0]
                print(f"   [ERROR] Không thành công trên {p.device}: {err_msg}")
                sys.stdout.flush()
                if inst:
                    try:
                        inst.serial.close()
                    except Exception:
                        pass

        print("[ERROR] PZEM: Không tìm thấy PZEM-017 trên bất kỳ cổng COM nào.")
        sys.stdout.flush()
        return None

    def connect(self):
        """Kết nối PZEM-017 qua USB."""
        if not MODBUS_AVAILABLE:
            print("[ERROR] minimalmodbus chưa cài — pip install minimalmodbus")
            sys.stdout.flush()
            return False

        try:
            # Đóng kết nối cũ nếu có
            if self.instrument:
                try:
                    self.instrument.serial.close()
                except Exception:
                    pass
                self.instrument = None

            if self.port == 'AUTO':
                self.instrument = self._find_pzem_port()
            else:
                print(f"[POWER] PZEM: Kết nối trực tiếp {self.port}...")
                sys.stdout.flush()
                self.instrument = self._create_instrument(self.port)
                # Thử đọc để xác nhận
                v = self.instrument.read_register(0x0000, functioncode=4)
                print(f"[OK] PZEM-017 kết nối thành công trên {self.port}. Điện áp: {v*0.01:.2f}V")
                sys.stdout.flush()

            if self.instrument:
                self._connected = True
                return True

        except Exception as e:
            err_msg = str(e).strip().split('\n')[0]
            print(f"[ERROR] Lỗi kết nối PZEM trên {self.port}: {err_msg}")
            sys.stdout.flush()
            if self.instrument:
                try:
                    self.instrument.serial.close()
                except Exception:
                    pass
                self.instrument = None

        self._connected = False
        return False

    # ── Đọc dữ liệu ──

    def read_power(self):
        """Đọc Voltage, Current, Power, Energy từ PZEM-017 qua Modbus RTU."""
        if not self.instrument or not self._connected:
            return None

        try:
            with self._lock:
                # Đọc 6 input registers liên tiếp (0x0000 → 0x0005)
                data = self.instrument.read_registers(
                    0x0000, 6, functioncode=4
                )

            # Parse theo datasheet PZEM-017
            voltage = data[0] * 0.01                          # V
            current = data[1] * 0.01                          # A
            power   = ((data[3] << 16) | data[2]) * 0.1       # W
            energy  = ((data[5] << 16) | data[4]) / 1000.0    # Wh → kWh

            reading = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'voltage': round(voltage, 2),
                'current': round(current, 3),
                'power': round(power, 1),
                'energy': round(energy, 3),
            }

            self.current = reading
            self.history.append(reading)
            return reading

        except Exception as e:
            print(f"[ERROR] PZEM read error: {e}")
            sys.stdout.flush()
            self._connected = False
            return None

    def get_average_power(self, minutes=5):
        """Tính công suất trung bình trong N phút gần nhất."""
        cutoff = time.time() - (minutes * 60)
        recent = []
        for r in self.history:
            try:
                ts = datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S').timestamp()
                if ts > cutoff:
                    recent.append(r['power'])
            except Exception:
                pass
        return sum(recent) / len(recent) if recent else 0.0

    # ── Thread control ──

    def start(self):
        """Bắt đầu đọc power định kỳ (background thread — không block main thread)."""
        if self._running:
            return
        self._running = True

        print("[POWER] PowerMonitor: Khởi động background thread (tự kết nối PZEM-017)...")
        sys.stdout.flush()

        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Dừng đọc."""
        self._running = False
        if self.instrument:
            try:
                self.instrument.serial.close()
            except Exception:
                pass

    def _read_loop(self):
        """Thread đọc power mỗi N giây, tự reconnect khi mất kết nối."""
        _reconnect_interval = 30   # Thử kết nối lại mỗi 30s
        _last_reconnect = 0

        _last_stats_update = 0     # Thời điểm cuối cùng cập nhật stats

        while self._running:
            try:
                reading = None

                if self._connected:
                    reading = self.read_power()

                # Nếu chưa kết nối hoặc đọc lỗi → thử reconnect
                if reading is None:
                    now = time.time()
                    if now - _last_reconnect >= _reconnect_interval:
                        _last_reconnect = now
                        if self.connect():
                            port_name = self.instrument.serial.port if self.instrument else '?'
                            print(f"[POWER] PowerMonitor: PZEM-017 kết nối OK trên {port_name}")
                            sys.stdout.flush()
                            continue  # Đọc ngay sau khi kết nối

                    # Giữ giá trị = 0
                    reading = {
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'voltage': 0.0,
                        'current': 0.0,
                        'power': 0.0,
                        'energy': 0.0,
                    }
                    self.current = reading

                # Lưu vào SQLite
                insert_power_reading(
                    reading['voltage'],
                    reading['current'],
                    reading['power'],
                    reading['energy']
                )
                
                # Cập nhật daily stats tối đa 1 lần mỗi 60 giây để tránh ghi DB liên tục
                now = time.time()
                if now - _last_stats_update >= 60:
                    update_daily_stats()
                    _last_stats_update = now

            except Exception as e:
                print(f"[ERROR] Power read loop error: {e}")
                sys.stdout.flush()

            time.sleep(self._read_interval)


# ==================== CLEANING EFFICIENCY TRACKER ====================

class CleaningEfficiencyTracker:
    """
    Theo dõi hiệu suất vệ sinh: đo công suất trước/sau.
    Workflow:
      1. on_cleaning_started() — ghi lại P_trước
      2. Đợi POST_CLEAN_DELAY giây (mặc định 300s = 5 phút)
      3. on_cleaning_finished() — đo P_sau, tính ΔP và η%
    """

    def __init__(self, power_monitor, config):
        self.pm = power_monitor
        self.config = config
        self.post_clean_delay = config.get('POST_CLEAN_DELAY', 60)
        self._pending_event = None
        self._timer = None

        # Kết quả gần nhất
        self.last_event = None

    def on_cleaning_started(self, trigger_reason='', dirty_ratio=0.0,
                            ai_label='', ai_confidence=0.0, snapshot_file=''):
        """Gọi khi PLC bắt đầu vệ sinh — ghi lại P_trước."""
        pre_power = self.pm.get_average_power(minutes=(self.post_clean_delay / 60.0))

        self._pending_event = {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': None,
            'trigger_reason': trigger_reason,
            'dirty_ratio': dirty_ratio,
            'pre_clean_power': round(pre_power, 1),
            'post_clean_power': 0.0,
            'power_gain': 0.0,
            'improvement_pct': 0.0,
            'ai_label': ai_label,
            'ai_confidence': ai_confidence,
            'snapshot_file': snapshot_file,
        }

        print(f"[POWER] Efficiency: Ghi nhận P_trước = {pre_power:.1f}W")
        print(f"[POWER] Efficiency: Sẽ đo P_sau sau {self.post_clean_delay}s...")

        # Đặt timer để đo sau N giây
        self._timer = threading.Timer(self.post_clean_delay, self._measure_post_clean)
        self._timer.daemon = True
        self._timer.start()

    def _measure_post_clean(self):
        """Đo công suất sau vệ sinh (gọi tự động sau delay)."""
        if self._pending_event is None:
            return

        post_power = self.pm.get_average_power(minutes=(self.post_clean_delay / 60.0))
        event = self._pending_event

        event['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event['post_clean_power'] = round(post_power, 1)

        pre = event['pre_clean_power']
        if pre > 0:
            gain = post_power - pre
            improvement = (gain / pre) * 100
        else:
            gain = 0.0
            improvement = 0.0

        event['power_gain'] = round(gain, 1)
        event['improvement_pct'] = round(improvement, 1)

        # Lưu vào SQLite
        insert_cleaning_event(event)

        self.last_event = event
        self._pending_event = None

        print(f"[POWER] Efficiency: P_sau = {post_power:.1f}W | "
              f"ΔP = {gain:+.1f}W | η = {improvement:+.1f}%")

    def get_last_event(self):
        """Trả về sự kiện vệ sinh gần nhất (hoặc None)."""
        if self.last_event:
            return self.last_event
        # Fallback: đọc từ DB
        events = get_cleaning_events(limit=1)
        return events[0] if events else None
