"""
closed_loop_engine.py — Closed-Loop Supervisory Engine for SolarClean System
=============================================================================
Điều phối Chu trình Khép kín (Closed-Loop Supervisory Control):
  1. Giám sát / Phát hiện bẩn (AI Perception)
  2. Ghi nhận dữ liệu ban đầu (P_trước, Bẩn_trước, Ảnh trước)
  3. Kích hoạt cơ cấu vệ sinh (PLC S7-1200 Execution)
  4. Chờ cơ cấu về Home & ráo nước (Settle Delay)
  5. Hậu kiểm AI tức thời (Post-Cleaning Inspection)
  6. Đánh giá điều kiện nghiệm thu (Acceptance Evaluation):
     - Nếu ĐẠT (NFO <= Ngưỡng & sạch vật cản): Ghi nhận Thành công, lưu DB, báo Zalo/Web
     - Nếu CHƯA ĐẠT và k < Max: Tự động lau lại lần k + 1
     - Nếu CHƯA ĐẠT và k >= Max: Báo động Vết bẩn cứng đầu (Persistent Dirt Alarm)
"""

import os
import sys
import time
import threading
from datetime import datetime
from typing import Callable, Optional, Dict, Any, List

def _configure_console_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_configure_console_encoding()

# Các trạng thái của Chu trình khép kín
STATE_IDLE = "IDLE"              # Hệ thống sẵn sàng / Giám sát thời gian thực
STATE_TRIGGERED = "TRIGGERED"    # Phát hiện bẩn, chuẩn bị chu trình
STATE_CLEANING = "CLEANING"      # PLC đang điều khiển robot quét/bơm nước
STATE_SETTLING = "SETTLING"      # Chờ robot về vị trí Home và bề mặt ráo nước
STATE_INSPECTING = "INSPECTING"  # Camera chụp ảnh hậu kiểm & AI quét đánh giá
STATE_SUCCESS = "SUCCESS"        # Nghiệm thu ĐẠT tiêu chuẩn
STATE_RETRYING = "RETRYING"      # Hậu kiểm chưa đạt, kích hoạt lau lại
STATE_ALARM = "ALARM"            # Vượt quá số lần thử, cảnh báo can thiệp thủ công

STATE_NAMES_VI = {
    STATE_IDLE: "SẴN SÀNG / GIÁM SÁT",
    STATE_TRIGGERED: "PHÁT HIỆN BẨN",
    STATE_CLEANING: "ĐANG VỆ SINH (PLC)",
    STATE_SETTLING: "CHỜ ỔN ĐỊNH BỀ MẶT",
    STATE_INSPECTING: "HẬU KIỂM AI",
    STATE_SUCCESS: "NGHIỆM THU ĐẠT",
    STATE_RETRYING: "ĐANG LAU LẠI",
    STATE_ALARM: "CẢNH BÁO BẨN CỨNG ĐẦU"
}

STATE_COLORS = {
    STATE_IDLE: "#64748b",        # Slate
    STATE_TRIGGERED: "#f59e0b",   # Amber
    STATE_CLEANING: "#0284c7",    # Sky Blue
    STATE_SETTLING: "#6366f1",    # Indigo
    STATE_INSPECTING: "#8b5cf6",  # Violet
    STATE_SUCCESS: "#10b981",     # Emerald
    STATE_RETRYING: "#eab308",    # Yellow
    STATE_ALARM: "#ef4444"        # Crimson Red
}


class ClosedLoopEngine:
    def __init__(self,
                 plc_controller=None,
                 power_monitor=None,
                 get_frame_func: Optional[Callable[[], Any]] = None,
                 inspect_frame_func: Optional[Callable[[Any], Dict[str, Any]]] = None,
                 config: Optional[Dict[str, Any]] = None,
                 zalo_service=None,
                 snapshot_folder: str = "snapshots"):
        self.plc = plc_controller
        self.power_monitor = power_monitor
        self.get_frame_func = get_frame_func
        self.inspect_frame_func = inspect_frame_func
        self.config = config or {}
        self.zalo = zalo_service
        self.snapshot_folder = snapshot_folder
        os.makedirs(self.snapshot_folder, exist_ok=True)

        # Cấu hình chu trình khép kín
        self.max_retries = int(self.config.get('MAX_CLEANING_RETRIES', 2))
        self.acceptance_dirt_threshold = float(self.config.get('ACCEPTANCE_DIRT_THRESHOLD', 0.05))
        self.settle_delay_seconds = float(self.config.get('POST_CLEAN_SETTLE_DELAY', 8.0))

        # Runtime State
        self.state = STATE_IDLE
        self.current_retry = 0
        self.cycle_in_progress = False
        self.stop_requested = False
        self.last_cycle_summary: Optional[Dict[str, Any]] = None

        # Lock & Thread
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        # Callbacks
        self._state_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        self._log_callbacks: List[Callable[[str, str], None]] = []
        self._inspection_callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_state_callback(self, cb: Callable[[str, Dict[str, Any]], None]):
        """Đăng ký callback nhận sự kiện thay đổi trạng thái (cho UI)."""
        if cb not in self._state_callbacks:
            self._state_callbacks.append(cb)

    def register_log_callback(self, cb: Callable[[str, str], None]):
        """Đăng ký callback nhận thông điệp log (level, text)."""
        if cb not in self._log_callbacks:
            self._log_callbacks.append(cb)

    def register_inspection_callback(self, cb: Callable[[Dict[str, Any]], None]):
        """Đăng ký callback nhận kết quả trước/sau sau mỗi lần hậu kiểm."""
        if cb not in self._inspection_callbacks:
            self._inspection_callbacks.append(cb)

    def log(self, level: str, message: str):
        """Gửi log ra console và các listener."""
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] [{level}] {message}"
        try:
            print(f"[CLOSED-LOOP] ClosedLoop: {full_msg}")
        except Exception:
            pass
        for cb in self._log_callbacks:
            try:
                cb(level, message)
            except Exception:
                pass

    def _set_state(self, new_state: str, extra_data: Optional[Dict[str, Any]] = None):
        with self._lock:
            self.state = new_state
        data = {
            'state': new_state,
            'state_name': STATE_NAMES_VI.get(new_state, new_state),
            'state_color': STATE_COLORS.get(new_state, "#64748b"),
            'retry_count': self.current_retry,
            'max_retries': self.max_retries,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if extra_data:
            data.update(extra_data)

        for cb in self._state_callbacks:
            try:
                cb(new_state, data)
            except Exception as e:
                try:
                    print(f"Callback state error: {e}")
                except Exception:
                    pass

    def get_status_dict(self) -> Dict[str, Any]:
        """Trả về thông tin trạng thái phục vụ API / UI."""
        return {
            'state': self.state,
            'state_name': STATE_NAMES_VI.get(self.state, self.state),
            'state_color': STATE_COLORS.get(self.state, "#64748b"),
            'is_running': self.cycle_in_progress,
            'current_retry': self.current_retry,
            'max_retries': self.max_retries,
            'acceptance_threshold': self.acceptance_dirt_threshold,
            'settle_delay': self.settle_delay_seconds,
            'last_cycle': self.last_cycle_summary
        }

    def start_cycle(self,
                    trigger_source: str = "Thủ công",
                    pre_frame=None,
                    pre_dirt_ratio: float = 0.0,
                    pre_label: str = "",
                    pre_confidence: float = 0.0,
                    pre_faults: Optional[List[str]] = None) -> bool:
        """Kích hoạt chu trình khép kín trong thread riêng."""
        with self._lock:
            if self.cycle_in_progress:
                self.log("WARN", "Chu trình khép kín đang thực thi, bỏ qua lệnh kích hoạt mới.")
                return False
            self.cycle_in_progress = True
            self.stop_requested = False
            self.current_retry = 0

        self._thread = threading.Thread(
            target=self._run_cycle,
            args=(trigger_source, pre_frame, pre_dirt_ratio, pre_label, pre_confidence, pre_faults or []),
            name="ClosedLoopWorker",
            daemon=True
        )
        self._thread.start()
        return True

    def cancel_cycle(self):
        """Hủy chu trình đang chạy an toàn."""
        self.stop_requested = True
        self.log("WARN", "Đã nhận lệnh hủy chu trình khép kín từ người vận hành.")

    def _read_current_power(self) -> float:
        """Đọc công suất thực tế tức thời từ PZEM-017 hoặc PLC."""
        # Ưu tiên đọc từ PowerMonitor
        if self.power_monitor:
            try:
                last_reading = getattr(self.power_monitor, 'last_power', None)
                if last_reading is not None and last_reading > 0:
                    return float(last_reading)
                avg = self.power_monitor.get_average_power(minutes=1)
                if avg > 0:
                    return float(avg)
            except Exception:
                pass

        # Fallback đọc từ PLC
        if self.plc and getattr(self.plc, 'is_connected', False):
            try:
                pdata = self.plc.read_power()
                if pdata and 'power' in pdata:
                    return float(pdata['power'])
            except Exception:
                pass
        return 0.0

    def _sleep_with_cancel(self, seconds: float) -> bool:
        """Sleep từng đoạn 0.2s để phản hồi ngay nếu có lệnh hủy."""
        steps = int(seconds / 0.2)
        for _ in range(max(1, steps)):
            if self.stop_requested:
                return False
            time.sleep(0.2)
        return not self.stop_requested

    def _save_image_file(self, filepath: str, img: Any):
        """Lưu hình ảnh hỗ trợ cả OpenCV và Pillow an toàn."""
        if img is None:
            return
        try:
            import cv2
            cv2.imwrite(filepath, img)
            return
        except Exception:
            pass

        try:
            from PIL import Image
            import numpy as np
            if isinstance(img, np.ndarray):
                if len(img.shape) == 3 and img.shape[2] == 3:
                    rgb = img[:, :, ::-1]
                else:
                    rgb = img
                pil_img = Image.fromarray(rgb)
                pil_img.save(filepath)
            elif isinstance(img, Image.Image):
                img.save(filepath)
        except Exception as e:
            self.log("WARN", f"Không thể lưu ảnh {filepath}: {e}")

    def _run_cycle(self, trigger_source, pre_frame, pre_dirt_ratio, pre_label, pre_confidence, pre_faults):
        cycle_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log("INFO", f"=== BẮT ĐẦU CHU TRÌNH KHÉP KÍN (ID: {cycle_id}) ===")
        self.log("INFO", f"Nguồn kích hoạt: {trigger_source} | Độ bẩn ban đầu: {pre_dirt_ratio*100:.1f}%")

        # 1. Ghi nhận dữ liệu ban đầu
        self._set_state(STATE_TRIGGERED, {'cycle_id': cycle_id, 'step': 1})
        pre_power = self._read_current_power()

        pre_snapshot_filename = f"pre_clean_{cycle_id}.jpg"
        pre_snapshot_path = os.path.join(self.snapshot_folder, pre_snapshot_filename)
        self._save_image_file(pre_snapshot_path, pre_frame)

        # Nếu chưa có frame hoặc chưa quét AI, thử quét nếu có inspect_frame_func
        if (pre_frame is None or pre_dirt_ratio <= 0) and self.get_frame_func and self.inspect_frame_func:
            current_live = self.get_frame_func()
            if current_live is not None:
                pre_frame = current_live
                ai_res = self.inspect_frame_func(pre_frame)
                pre_dirt_ratio = ai_res.get('area_ratio', 0.0)
                pre_label = ai_res.get('label_name', pre_label)
                pre_confidence = ai_res.get('confidence', pre_confidence)
                pre_faults = ai_res.get('clean_faults', pre_faults)
                try:
                    cv2.imwrite(pre_snapshot_path, pre_frame)
                except Exception:
                    pass

        self.log("INFO", f"Dữ liệu trước vệ sinh: P_trước = {pre_power:.1f}W, Bẩn = {pre_dirt_ratio*100:.1f}%, Lỗi = {pre_faults}")

        retry_k = 1
        cycle_success = False
        final_post_data = None

        has_leaf = 'leaf' in pre_faults or 'lá cây' in pre_faults
        has_bird = 'bird_drop' in pre_faults or 'phân chim' in pre_faults
        has_dirt = True

        while retry_k <= self.max_retries and not self.stop_requested:
            self.current_retry = retry_k
            self.log("INFO", f"--- TIẾN HÀNH VỆ SINH LẦN {retry_k}/{self.max_retries} ---")

            # 2. Gửi lệnh PLC
            self._set_state(STATE_CLEANING, {
                'cycle_id': cycle_id,
                'retry_k': retry_k,
                'max_retries': self.max_retries,
                'step': 2
            })

            plc_sent = False
            if self.plc and getattr(self.plc, 'is_connected', False):
                try:
                    plc_sent = self.plc.trigger_faults(has_dirt=has_dirt, has_leaf=has_leaf, has_bird_drop=has_bird)
                    if not plc_sent:
                        plc_sent = self.plc.trigger_cleaning()
                except Exception as e:
                    self.log("ERROR", f"Lỗi gửi lệnh PLC: {e}")
            else:
                self.log("WARN", "PLC chưa kết nối thực tế! Tiến hành mô phỏng chu trình lau.")
                plc_sent = True

            if plc_sent:
                self.log("INFO", f"PLC đã nhận lệnh vệ sinh lần {retry_k} thành công.")
            else:
                self.log("ERROR", f"Không thể kích hoạt PLC lần {retry_k}!")

            # 3. Chờ ráo nước & cơ cấu về Home
            self._set_state(STATE_SETTLING, {
                'cycle_id': cycle_id,
                'retry_k': retry_k,
                'settle_sec': self.settle_delay_seconds,
                'step': 3
            })
            self.log("INFO", f"Đang chờ cơ cấu hoàn tất hành trình và ráo nước ({self.settle_delay_seconds:.0f}s)...")
            if not self._sleep_with_cancel(self.settle_delay_seconds):
                self.log("WARN", "Chu trình bị hủy trong khi chờ settle.")
                break

            # 4. Hậu kiểm bằng AI (Post-Inspection)
            self._set_state(STATE_INSPECTING, {
                'cycle_id': cycle_id,
                'retry_k': retry_k,
                'step': 4
            })
            self.log("INFO", f"Tiến hành chụp ảnh hậu kiểm và quét AI sau lần lau {retry_k}...")

            post_frame = None
            if self.get_frame_func:
                post_frame = self.get_frame_func()

            post_dirt_ratio = 0.0
            post_label = "Clean"
            post_confidence = 0.95
            post_faults = []
            post_debug_frame = None

            if post_frame is not None and self.inspect_frame_func:
                try:
                    ai_post = self.inspect_frame_func(post_frame)
                    post_dirt_ratio = float(ai_post.get('area_ratio', 0.0))
                    post_label = ai_post.get('label_name', "sach")
                    post_confidence = float(ai_post.get('confidence', 0.90))
                    post_faults = ai_post.get('clean_faults', [])
                    post_debug_frame = ai_post.get('debug_frame', post_frame)
                except Exception as e:
                    self.log("ERROR", f"Lỗi quét AI hậu kiểm: {e}")
            else:
                # Mô phỏng giảm độ bẩn nếu không có camera thật
                simulated_ratio = max(0.01, pre_dirt_ratio * (0.35 ** retry_k))
                post_dirt_ratio = simulated_ratio
                post_label = "sach" if post_dirt_ratio <= self.acceptance_dirt_threshold else "ban"
                post_confidence = 0.92

            post_snapshot_filename = f"post_clean_{cycle_id}_try{retry_k}.jpg"
            post_snapshot_path = os.path.join(self.snapshot_folder, post_snapshot_filename)
            self._save_image_file(post_snapshot_path, post_frame)

            # 5. Đo công suất sau vệ sinh và tính chênh lệch
            post_power = self._read_current_power()
            gain = post_power - pre_power
            improvement = ((gain / pre_power) * 100.0) if pre_power > 0 else 0.0

            final_post_data = {
                'cycle_id': cycle_id,
                'retry_k': retry_k,
                'pre_power': pre_power,
                'post_power': post_power,
                'power_gain': round(gain, 2),
                'improvement_pct': round(improvement, 1),
                'pre_dirt_ratio': round(pre_dirt_ratio, 4),
                'post_dirt_ratio': round(post_dirt_ratio, 4),
                'acceptance_threshold': self.acceptance_dirt_threshold,
                'pre_snapshot_file': pre_snapshot_filename,
                'post_snapshot_file': post_snapshot_filename,
                'pre_frame': pre_frame,
                'post_frame': post_frame,
                'post_debug_frame': post_debug_frame,
                'post_faults': post_faults,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Bắn dữ liệu hậu kiểm về UI để hiển thị so sánh trước / sau
            for cb in self._inspection_callbacks:
                try:
                    cb(final_post_data)
                except Exception:
                    pass

            # 6. Đánh giá điều kiện nghiệm thu
            # Điều kiện: Tỷ lệ diện tích bẩn <= Ngưỡng nghiệm thu VÀ Không còn vật cản (lá, phân chim)
            is_dirt_pass = (post_dirt_ratio <= self.acceptance_dirt_threshold)
            is_obstacle_free = (len(post_faults) == 0)
            is_acceptable = is_dirt_pass and is_obstacle_free

            self.log("INFO", f"Kết quả hậu kiểm lần {retry_k}: Bẩn = {post_dirt_ratio*100:.1f}% "
                             f"(Ngưỡng: {self.acceptance_dirt_threshold*100:.1f}%), "
                             f"P = {post_power:.1f}W (ΔP: {gain:+.1f}W, {improvement:+.1f}%), "
                             f"Vật cản = {post_faults}")

            if is_acceptable:
                cycle_success = True
                self.log("INFO", f"[OK] NGHIỆM THU ĐẠT CHUẨN! Bề mặt sạch hoàn toàn sau {retry_k} lần lau.")
                break
            else:
                if retry_k < self.max_retries:
                    self._set_state(STATE_RETRYING, {
                        'cycle_id': cycle_id,
                        'retry_k': retry_k,
                        'next_retry': retry_k + 1,
                        'post_dirt': post_dirt_ratio,
                        'step': 5
                    })
                    self.log("WARN", f"[WARN] Hậu kiểm chưa đạt tiêu chuẩn. Chuẩn bị tự động lau lại lần {retry_k + 1}/{self.max_retries}...")
                    if self.zalo and hasattr(self.zalo, 'send_broadcast_message'):
                        try:
                            self.zalo.send_broadcast_message(
                                f"[WARN] [SolarClean] Hậu kiểm lần {retry_k} chưa đạt (Bẩn còn {post_dirt_ratio*100:.1f}%). "
                                f"Đang kích hoạt lau lại lần {retry_k + 1}/{self.max_retries}...",
                                alert_key="closed_loop_retry"
                            )
                        except Exception:
                            pass
                    time.sleep(2.0)
                    retry_k += 1
                else:
                    self.log("ERROR", f"[ERROR] ĐÃ ĐẠT SỐ LẦN LAU TỐI ĐA ({self.max_retries}) NHƯNG VẪN KHÔNG SẠCH!")
                    break

        # 7. Xử lý kết quả chung cuộc
        end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.stop_requested:
            final_status = "CANCELLED"
            self._set_state(STATE_IDLE, {'status': 'CANCELLED'})
            self.log("WARN", "Chu trình khép kín đã kết thúc do bị hủy.")
        elif cycle_success:
            final_status = "SUCCESS"
            self._set_state(STATE_SUCCESS, final_post_data or {})
            self.log("INFO", f"[SUCCESS] HOÀN THÀNH CHU TRÌNH KHÉP KÍN: THÀNH CÔNG (Sau {retry_k} lượt)!")

            # Lưu vào Database SQLite
            try:
                from power_db import insert_cleaning_event
                event_dict = {
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'trigger_reason': f"{trigger_source} (Chu trình khép kín - {retry_k} lượt)",
                    'dirty_ratio': float(pre_dirt_ratio),
                    'post_dirty_ratio': float(final_post_data.get('post_dirt_ratio', 0.0) if final_post_data else 0.0),
                    'pre_clean_power': float(pre_power),
                    'post_clean_power': float(final_post_data.get('post_power', 0.0) if final_post_data else 0.0),
                    'power_gain': float(final_post_data.get('power_gain', 0.0) if final_post_data else 0.0),
                    'improvement_pct': float(final_post_data.get('improvement_pct', 0.0) if final_post_data else 0.0),
                    'ai_label': "Sạch (Đã nghiệm thu)",
                    'ai_confidence': 1.0,
                    'snapshot_file': pre_snapshot_filename,
                    'post_snapshot_file': final_post_data.get('post_snapshot_file', '') if final_post_data else '',
                    'retries_used': retry_k,
                    'cycle_status': 'SUCCESS'
                }
                insert_cleaning_event(event_dict)
                self.log("INFO", "Đã lưu bản ghi chi tiết chu trình khép kín vào cơ sở dữ liệu.")
            except Exception as e:
                self.log("ERROR", f"Lỗi lưu DB: {e}")

            # Gửi Zalo thông báo thành công
            if self.zalo and hasattr(self.zalo, 'send_broadcast_message'):
                try:
                    gain_w = final_post_data.get('power_gain', 0.0) if final_post_data else 0.0
                    imp_pct = final_post_data.get('improvement_pct', 0.0) if final_post_data else 0.0
                    post_d = final_post_data.get('post_dirt_ratio', 0.0) if final_post_data else 0.0
                    msg = (
                        f"[OK] [SolarClean] VỆ SINH HOÀN TẤT THÀNH CÔNG!\n"
                        f"• Chu trình: Khép kín (Closed-Loop)\n"
                        f"• Số lần quét: {retry_k}/{self.max_retries}\n"
                        f"• Độ bẩn: {pre_dirt_ratio*100:.1f}% -> {post_d*100:.1f}%\n"
                        f"• Công suất: {pre_power:.1f}W -> {final_post_data.get('post_power', 0.0):.1f}W\n"
                        f"• Tăng trưởng ΔP: +{gain_w:.1f}W ({imp_pct:+.1f}%)\n"
                        f"• Trạng thái: Đạt chuẩn nghiệm thu"
                    )
                    self.zalo.send_broadcast_message(msg, alert_key="closed_loop_success")
                except Exception:
                    pass

        else:
            final_status = "ALARM_PERSISTENT_DIRT"
            self._set_state(STATE_ALARM, final_post_data or {})
            self.log("ERROR", "[ALARM] BÁO ĐỘNG: Bẩn cứng đầu không thể làm sạch tự động!")

            # Lưu vào Database với cờ cảnh báo
            try:
                from power_db import insert_cleaning_event
                event_dict = {
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'trigger_reason': f"{trigger_source} (CẢNH BÁO BẨN CỨNG ĐẦU)",
                    'dirty_ratio': float(pre_dirt_ratio),
                    'post_dirty_ratio': float(final_post_data.get('post_dirt_ratio', 0.0) if final_post_data else 0.0),
                    'pre_clean_power': float(pre_power),
                    'post_clean_power': float(final_post_data.get('post_power', 0.0) if final_post_data else 0.0),
                    'power_gain': float(final_post_data.get('power_gain', 0.0) if final_post_data else 0.0),
                    'improvement_pct': float(final_post_data.get('improvement_pct', 0.0) if final_post_data else 0.0),
                    'ai_label': "Bẩn cứng đầu (Alarm)",
                    'ai_confidence': 1.0,
                    'snapshot_file': pre_snapshot_filename,
                    'post_snapshot_file': final_post_data.get('post_snapshot_file', '') if final_post_data else '',
                    'retries_used': retry_k,
                    'cycle_status': 'ALARM_PERSISTENT_DIRT'
                }
                insert_cleaning_event(event_dict)
            except Exception as e:
                self.log("ERROR", f"Lỗi lưu DB alarm: {e}")

            # Gửi Zalo cảnh báo bảo trì khẩn
            if self.zalo and hasattr(self.zalo, 'send_broadcast_message'):
                try:
                    post_d = final_post_data.get('post_dirt_ratio', 0.0) if final_post_data else 0.0
                    msg = (
                        f"[ALARM] [SolarClean - CẢNH BÁO BẢO TRÌ]\n"
                        f"Hệ thống đã thử vệ sinh {self.max_retries} lần nhưng KHÔNG ĐẠT tiêu chuẩn nghiệm thu!\n"
                        f"• Độ bẩn còn lại: {post_d*100:.1f}% (Vượt ngưỡng {self.acceptance_dirt_threshold*100:.1f}%)\n"
                        f"• Khả năng: Vết bẩn bám dính nặng, dị vật dính chặt hoặc lỗi cơ cấu phun nước/gạt.\n"
                        f"• Đề nghị: Nhân viên kỹ thuật kiểm tra trực tiếp hiện trường!"
                    )
                    self.zalo.send_broadcast_message(msg, alert_key="closed_loop_alarm")
                except Exception:
                    pass

        # Lưu thông tin chu trình gần nhất
        if final_post_data:
            final_post_data['final_status'] = final_status
            self.last_cycle_summary = final_post_data

        with self._lock:
            self.cycle_in_progress = False

        # Sau 8 giây, nếu là SUCCESS hoặc ALARM thì reset về IDLE để tiếp tục giám sát bình thường
        time.sleep(8.0)
        with self._lock:
            if not self.cycle_in_progress and self.state in (STATE_SUCCESS, STATE_ALARM):
                self._set_state(STATE_IDLE)
