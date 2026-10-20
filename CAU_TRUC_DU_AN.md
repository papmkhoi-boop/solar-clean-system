# Cấu trúc dự án sau khi dọn

Ngày dọn dẹp gần nhất: **29/07/2026**

## Phần lõi cần giữ ở thư mục gốc (`d:\DuAn`)

| Mục | Vai trò |
|---|---|
| `solar_panel_plc_auto_tflite.py` | Ứng dụng GUI desktop chính (Tkinter/PyQt + PLC + AI) |
| `web_monitor_fastapi.py` | Backend Web/Mobile API (FastAPI) |
| `power_db.py` | Module quản lý cơ sở dữ liệu SQLite & đo đạc năng lượng |
| `cloud_api_client.py` | Client đồng bộ dữ liệu với server Cloud |
| `solar_power.db` | Cơ sở dữ liệu SQLite dữ liệu vận hành |
| `templates/` | Giao diện Web Monitor (HTML/JS/CSS) |
| `taikhoan/` | Thông tin tài khoản & session |
| `snapshots/` | Ảnh snapshot chụp runtime (desktop & web app đọc trực tiếp) |
| `solar_clean_rn/` | App mobile React Native / Expo |
| `solar_clean_cloud/` | Backend server Cloud |
| `website/` | Trang web giới thiệu dự án |
| `buiban.h5` | Mô hình CNN phân loại độ bẩn/sạch tấm pin |
| `panel 2.pt` | Mô hình YOLOv8-Seg phân vùng tấm pin |
| `Solar.pt` | Mô hình YOLOv8 Detect nhận diện vật cản/bụi |
| `labels.txt`, `labels_2classes.txt` | File nhãn phân loại AI |
| `snap7.dll` | Thư viện kết nối PLC Siemens S7 |
| `ctut.webp`, `SolarClean.ico` | Icon và hình ảnh giao diện chính |
| `requirements.txt` | Danh sách thư viện Python phụ thuộc |

## Các thư mục đã gom nhóm gọn gàng

| Thư mục | Nội dung |
|---|---|
| `docs/bai_bao_va_bao_cao/` | Bài báo khoa học, thuyết minh dự án, luận văn, các mẫu báo cáo CTUT |
| `logs/` | Tất cả file log runtime và log build (`app_debug.log`, `build_out.log`, `crash.log`, v.v.) |
| `tools/` | Script kiểm tra, test PZEM (`test_pzem.py`, `run_debug.py`), tool đo đạc |
| `data_samples/` | Bộ ảnh mẫu `anh_32_patch`, ảnh test thủ công |
| `packaging/pyinstaller/` | File `.spec` đóng gói PyInstaller (`SolarClean.spec`, `check_com_ports.spec`) |
| `backups/` | Các bản sao lưu `.bak` |
| `releases/` | File nén release, APK, artifact phát hành |
| `_archive_20260505/` | Archive bản build cũ và prototype cũ |

## Cách chạy nhanh

```text
python solar_panel_plc_auto_tflite.py
```

Web monitor sẽ được desktop app tự động khởi động tại:

```text
http://localhost:5000
```

## Ghi chú

- Giữ nguyên `venv/`, `.venv/`, `solar_clean_rn/node_modules/` để không ảnh hưởng môi trường Python và React Native.
- Giữ nguyên `snapshots/` ở gốc vì ứng dụng đọc/ghi trực tiếp vào đường dẫn tương đối `snapshots/`.

