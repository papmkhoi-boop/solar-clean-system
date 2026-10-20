import cv2
import numpy as np
from ultralytics import YOLO
import os
import time
from datetime import datetime

# --- CONFIGURATION ---
MODEL_PATH = 'panel 2.pt'  # Tên file model YOLO segmentation
CONF_THRESHOLD = 0.25      # Ngưỡng tin cậy để hiển thị kết quả

def test_yolo_live():
    # 1. Tải mô hình
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Không tìm thấy model: {MODEL_PATH}")
        return
    
    print(f"🔄 Đang tải mô hình {MODEL_PATH}...")
    model = YOLO(MODEL_PATH)
    print("✅ Đã tải mô hình xong.")

    # 2. Khởi tạo Camera
    camera_id = 0
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    output_dir = 'test_yolo_results'
    os.makedirs(output_dir, exist_ok=True)

    print("\n--- LIVE YOLO TEST TOOL ---")
    print("⌨️  Phím nhấn:")
    print("   [SPACE] : Chụp và chạy YOLO phân tích")
    print("   [C]     : Đổi Camera (Switch)")
    print("   [Q]     : Thoát chương trình")
    print("---------------------------")

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"⚠️ Lỗi đọc Camera {camera_id}. Đang thử chuyển...")
            camera_id = (camera_id + 1) % 4
            cap.release()
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            time.sleep(1)
            continue

        # Hiển thị live preview
        display_frame = frame.copy()
        cv2.putText(display_frame, f"CAM ID: {camera_id} | Live Feed", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(display_frame, "SPACE: Test YOLO | C: Switch | Q: Quit", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        cv2.imshow("LIVE FEED - Press SPACE to Test YOLO", display_frame)

        key = cv2.waitKey(1) & 0xFF

        # --- NHẤN SPACE: CHẠY YOLO ---
        if key == ord(' '):
            print(f"\n🔍 Đang phân tích khung hình từ Cam {camera_id}...")
            
            # Chạy inference
            results = model(frame, conf=CONF_THRESHOLD, verbose=False)[0]
            
            # Vẽ kết quả
            res_img = results.plot()
            
            # Kiểm tra xem có phát hiện được gì không
            found = results.masks is not None and len(results.masks) > 0
            msg = f"Detect: {len(results.masks) if found else 0} panels"
            color = (0, 255, 0) if found else (0, 0, 255)
            
            cv2.putText(res_img, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            
            # Hiển thị kết quả trong cửa sổ mới
            cv2.imshow("YOLO RESULT (Press any key to close)", res_img)
            
            # Lưu lại để xem sau
            timestamp = datetime.now().strftime("%H%M%S")
            save_path = os.path.join(output_dir, f"test_{timestamp}_cam{camera_id}.jpg")
            cv2.imwrite(save_path, res_img)
            print(f"✅ Đã lưu kết quả tại: {save_path}")
            
            cv2.waitKey(0) # Đợi người dùng nhấn phím bất kỳ để tiếp tục live
            cv2.destroyWindow("YOLO RESULT (Press any key to close)")

        # --- NHẤN C: ĐỔI CAMERA ---
        elif key == ord('c'):
            camera_id = (camera_id + 1) % 4
            print(f"🔄 Đổi sang Camera ID: {camera_id}")
            cap.release()
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        # --- NHẤN Q: THOÁT ---
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_yolo_live()
