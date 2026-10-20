import cv2
import os
import time
from datetime import datetime

def camera_capture():
    # 1. Khởi tạo
    camera_id = 0  # Thay đổi nếu bạn dùng camera khác
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW) # Dùng DSHOW cho Windows để mở nhanh hơn
    
    if not cap.isOpened():
        print(f"❌ Không thể mở camera ID {camera_id}")
        return

    # Thiết lập độ phân giải cao nếu camera hỗ trợ
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    output_dir = 'captured_images'
    os.makedirs(output_dir, exist_ok=True)

    print("--- CAMERA CAPTURE TOOL ---")
    print(f"📷 Camera ID: {camera_id}")
    print(f"📂 Thư mục lưu: {output_dir}")
    print("⌨️  Phím nhấn:")
    print("   [SPACE] : Chụp và lưu ảnh")
    print("   [C]     : Đổi Camera (Switch)")
    print("   [Q]     : Thoát chương trình")
    print("---------------------------")

    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"❌ Lỗi khi đọc từ camera ID {camera_id}. Tự động chuyển camera...")
            time.sleep(1)
            camera_id = (camera_id + 1) % 4
            cap.release()
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            continue

        # Hiển thị hướng dẫn lên màn hình
        display_frame = frame.copy()
        cv2.putText(display_frame, f"CAM ID: {camera_id} | Captured: {count}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, "SPACE: Capture | C: Switch Cam | Q: Quit", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow("Camera Realtime - Press SPACE to Capture", display_frame)

        key = cv2.waitKey(1) & 0xFF
        
        # Nhấn SPACE để chụp
        if key == ord(' '):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"capture_cam{camera_id}_{timestamp}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            # Lưu ảnh gốc (không có text overlay)
            cv2.imwrite(filepath, frame)
            count += 1
            print(f"📸 Đã lưu (Cam {camera_id}): {filename}")
            
            # Hiệu ứng nháy trắng khi chụp
            flash = np.full(frame.shape, 255, dtype=np.uint8)
            cv2.imshow("Camera Realtime - Press SPACE to Capture", flash)
            cv2.waitKey(50)

        # Nhấn C để đổi camera
        elif key == ord('c'):
            camera_id = (camera_id + 1) % 4 # Xoay vòng từ 0-3
            print(f"🔄 Đang chuyển sang Camera ID: {camera_id}...")
            cap.release()
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        # Nhấn Q để thoát
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n✅ Đã dừng. Tổng số ảnh đã chụp: {count}")

if __name__ == "__main__":
    import numpy as np
    camera_capture()
