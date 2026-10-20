"""
Test PZEM-017 trên COM7 (USB-SERIAL CH340)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import minimalmodbus
import serial

PORT = 'COM6'

print(f"=== TEST PZEM-017 trên {PORT} ===\n")

# Test 1: Mở port
print("1. Mở COM port...")
try:
    ser = serial.Serial(PORT, 9600, bytesize=8, parity='N', stopbits=2, timeout=1)
    print(f"   OK: {PORT} mở thành công")
    ser.close()
except serial.SerialException as e:
    print(f"   LỖI: {e}")
    print("\n   => COM port đang bị chiếm bởi chương trình khác!")
    print("   => Hãy tắt solar_panel_plc_auto_tflite.py trước rồi chạy lại.")
    input("\nNhấn Enter để thoát...")
    sys.exit(1)

# Test 2: Thử các slave address phổ biến + các baud rate
print("\n2. Thử đọc PZEM-017...")
BAUD_RATES = [9600]
SLAVE_ADDRS = [0x01, 0x02, 0x03, 0xF8, 0x00]  # 0xF8 = broadcast, 0x01 = default

for baud in BAUD_RATES:
    for addr in SLAVE_ADDRS:
        try:
            inst = minimalmodbus.Instrument(PORT, addr)
            inst.serial.baudrate = baud
            inst.serial.bytesize = 8
            inst.serial.parity = serial.PARITY_NONE
            inst.serial.stopbits = 2
            inst.serial.timeout = 1.5
            inst.mode = minimalmodbus.MODE_RTU
            inst.clear_buffers_before_each_transaction = True

            # Đọc voltage register
            v = inst.read_register(0x0000, functioncode=4)
            print(f"   THANH CONG! Baud={baud}, Addr={addr:#04x}")
            print(f"   Voltage raw = {v} -> {v * 0.01:.2f} V")

            # Đọc thêm 6 registers
            data = inst.read_registers(0x0000, 6, functioncode=4)
            voltage = data[0] * 0.01
            current = data[1] * 0.01
            power = ((data[3] << 16) | data[2]) * 0.1
            energy_wh = (data[5] << 16) | data[4]

            print(f"\n   === KET QUA ===")
            print(f"   Voltage: {voltage:.2f} V")
            print(f"   Current: {current:.3f} A")
            print(f"   Power:   {power:.1f} W")
            print(f"   Energy:  {energy_wh} Wh ({energy_wh/1000:.3f} kWh)")
            print(f"\n   PZEM-017 HOAT DONG BINH THUONG!")

            inst.serial.close()
            input("\nNhấn Enter để thoát...")
            sys.exit(0)

        except Exception as e:
            err = str(e).split('\n')[0][:80]
            print(f"   Baud={baud} Addr={addr:#04x}: {err}")
            try:
                inst.serial.close()
            except:
                pass

print("\n   Khong tim thay PZEM-017!")
print("   Kiem tra:")
print("   - Day noi PZEM A/B co dung khong?")
print("   - PZEM co duoc cap nguon khong?")
print("   - Thu doi day A va B (dao cuc)")
input("\nNhấn Enter để thoát...")
