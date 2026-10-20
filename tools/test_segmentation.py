import cv2
import numpy as np
from ultralytics import YOLO
import os
import glob
import time
from datetime import datetime

# --- CONFIGURATION ---
MODEL_PATH = 'panel 2.pt'  # Đảm bảo file này nằm cùng thư mục hoặc đúng đường dẫn
SOURCE_PATH = 'snapshots'   # Thư mục chứa ảnh test hoặc đường dẫn đến 1 file ảnh cụ thể
OUTPUT_DIR = 'test_results_seg'
CONF_THRESHOLD = 0.25      # Ngưỡng tin cậy

def run_test():
    # 1. Khởi tạo
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Lỗi: Không tìm thấy mô hình tại {MODEL_PATH}")
        return

    print(f"🔄 Đang tải mô hình: {MODEL_PATH}...")
    try:
        model = YOLO(MODEL_PATH)
    except Exception as e:
        print(f"❌ Lỗi khi tải mô hình: {e}")
        return

    # 2. Xác định nguồn ảnh
    if os.path.isfile(SOURCE_PATH):
        image_paths = [SOURCE_PATH]
    elif os.path.isdir(SOURCE_PATH):
        image_paths = glob.glob(os.path.join(SOURCE_PATH, "*.jpg")) + \
                      glob.glob(os.path.join(SOURCE_PATH, "*.png")) + \
                      glob.glob(os.path.join(SOURCE_PATH, "*.jpeg"))
    else:
        print(f"❌ Lỗi: Nguồn ảnh {SOURCE_PATH} không hợp lệ.")
        return

    if not image_paths:
        print(f"⚠️ Không tìm thấy ảnh nào trong {SOURCE_PATH}")
        return

    print(f"🚀 Bắt đầu test {len(image_paths)} ảnh...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success_count = 0
    start_time = time.time()

    for i, img_path in enumerate(image_paths):
        filename = os.path.basename(img_path)
        print(f"[{i+1}/{len(image_paths)}] Đang xử lý: {filename}...", end='\r')
        
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"\n❌ Không thể đọc ảnh: {filename}")
            continue

        # 3. Chạy inference
        results = model(frame, conf=CONF_THRESHOLD, verbose=False)[0]

        # 4. Lưu kết quả
        annotated_frame = results.plot()
        
        if results.masks is not None:
            success_count += 1
            # Lưu ảnh đã vẽ bounding box và mask
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"res_{filename}"), annotated_frame)
            
            # Lưu mask riêng (nếu cần kiểm tra mask nhị phân)
            for j, mask in enumerate(results.masks.data):
                mask_np = mask.cpu().numpy()
                mask_resized = cv2.resize(mask_np, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)
                mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255
                cv2.imwrite(os.path.join(OUTPUT_DIR, f"mask_{j}_{filename}"), mask_binary)
        else:
            # Lưu ảnh gốc nhưng ghi chữ "No Detection" để dễ theo dõi
            cv2.putText(annotated_frame, "NO DETECTION", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
            cv2.imwrite(os.path.join(OUTPUT_DIR, f"fail_{filename}"), annotated_frame)

    total_time = time.time() - start_time
    print(f"\n\n✅ Hoàn thành!")
    print(f"--------------------------------------")
    print(f"📊 Tổng số ảnh: {len(image_paths)}")
    print(f"✅ Phát hiện được: {success_count}")
    print(f"❌ Không phát hiện: {len(image_paths) - success_count}")
    print(f"⏱️ Tổng thời gian: {total_time:.2f}s (Trung bình: {total_time/len(image_paths):.2f}s/ảnh)")
    print(f"📂 Kết quả đã lưu tại thư mục: {OUTPUT_DIR}")
    print(f"--------------------------------------")

if __name__ == "__main__":
    run_test()
