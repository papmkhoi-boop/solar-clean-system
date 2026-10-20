import os
import sys
import platform
import numpy as np

def _configure_console_encoding():
    """Keep Windows consoles/log capture from crashing on Vietnamese text or symbols."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_configure_console_encoding()

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

def check_env():
    print("=" * 60)
    print("HỆ THỐNG KIỂM TRA ĐỒNG BỘ MÔI TRƯỜNG DỰ ÁN SOLAR CLEAN")
    print("=" * 60)
    
    # 1. Hệ điều hành & Phần cứng
    print(f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    print(f"Processor: {platform.processor()}")
    print(f"Python version: {sys.version}")
    
    # 2. Phiên bản thư viện
    print("\n--- Phiên bản các thư viện chính ---")
    
    try:
        import tensorflow as tf
        print(f"TensorFlow: {tf.__version__}")
        try:
            print(f"Keras: {tf.keras.__version__}")
        except AttributeError:
            try:
                import keras
                print(f"Keras (Standalone): {keras.__version__}")
            except ImportError:
                print("Keras version: Unknown")
    except ImportError:
        print("TensorFlow: NOT INSTALLED")
        
    try:
        import cv2
        print(f"OpenCV (cv2): {cv2.__version__}")
    except ImportError:
        print("OpenCV (cv2): NOT INSTALLED")
        
    try:
        import PIL
        print(f"Pillow (PIL): {PIL.__version__}")
    except ImportError:
        print("Pillow (PIL): NOT INSTALLED")
        
    print(f"NumPy: {np.__version__}")
    
    # 3. Test Load Model & Kiểm tra độ chính xác (Inference Test)
    print("\n--- Kiểm tra độ chính xác của Model (Inference Test) ---")
    model_path = r"d:\DuAn\buiban.h5"
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(__file__), "..", "buiban.h5")
        
    if os.path.exists(model_path):
        try:
            import tensorflow as tf
            # Tạo dữ liệu giả định chuẩn (Fixed dummy input)
            dummy_input = np.ones((1, 224, 224, 3), dtype=np.float32)
            
            print(f"Đang thử tải model từ: {model_path}")
            # Thử load trực tiếp
            try:
                model = tf.keras.models.load_model(model_path)
                print("-> Trạng thái load model: THÀNH CÔNG trực tiếp (Load Model)")
                loaded_direct = True
            except Exception as e:
                print(f"-> Trạng thái load model trực tiếp: THẤT BẠI ({e})")
                print("-> Thử nạp bằng cơ chế load_weights thủ công...")
                loaded_direct = False
                
            # Chạy thử prediction với dữ liệu cố định (mảng toàn số 1)
            if loaded_direct:
                pred = model.predict(dummy_input, verbose=0)
                print(f"-> Kết quả dự đoán trên dữ liệu test cố định: {pred[0]}")
                print(f"   (Xác suất Lớp Sạch: {pred[0][0]:.6f} | Lớp Bẩn: {pred[0][1]:.6f})")
            else:
                # Dựng lại kiến trúc để test load weights
                from tensorflow.keras import layers
                from tensorflow.keras.applications import EfficientNetB0
                
                data_augmentation = tf.keras.Sequential([
                    layers.RandomFlip("horizontal_and_vertical"),
                    layers.RandomRotation(0.2),
                ])
                base_model = EfficientNetB0(input_shape=(224, 224, 3), include_top=False, weights=None)
                base_model._name = "functional"
                inputs = tf.keras.Input(shape=(224, 224, 3))
                x = data_augmentation(inputs)
                x = base_model(x, training=False)
                x = layers.GlobalAveragePooling2D()(x)
                x = layers.Dropout(0.2)(x)
                outputs = layers.Dense(2, activation='softmax')(x)
                test_model = tf.keras.Model(inputs, outputs)
                
                try:
                    test_model.load_weights(model_path)
                    pred = test_model.predict(dummy_input, verbose=0)
                    print("-> Trạng thái load model: THÀNH CÔNG bằng load_weights")
                    print(f"-> Kết quả dự đoán trên dữ liệu test cố định: {pred[0]}")
                    print(f"   (Xác suất Lớp Sạch: {pred[0][0]:.6f} | Lớp Bẩn: {pred[0][1]:.6f})")
                except Exception as w_err:
                    print(f"-> Trạng thái load weights: THẤT BẠI ({w_err})")
        except Exception as tf_err:
            print(f"Lỗi kiểm tra TensorFlow: {tf_err}")
    else:
        print(f"Không tìm thấy file model tại: {model_path}")
        
    # 4. Kiểm tra camera (nếu cắm chung)
    print("\n--- Kiểm tra Camera & OpenCV Backend ---")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = cap.get(cv2.CAP_PROP_FPS)
            brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
            contrast = cap.get(cv2.CAP_PROP_CONTRAST)
            exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
            backend_name = cap.getBackendName()
            
            print(f"Trạng thái camera: ĐÃ KẾT NỐI")
            print(f"Backend OpenCV đang dùng: {backend_name}")
            print(f"Độ phân giải mặc định: {w}x{h}")
            print(f"FPS mặc định: {fps}")
            print(f"Độ sáng mặc định (Brightness): {brightness}")
            print(f"Độ tương phản mặc định (Contrast): {contrast}")
            print(f"Độ phơi sáng mặc định (Exposure): {exposure}")
            cap.release()
        else:
            print("Trạng thái camera: KHÔNG THỂ MỞ (Kiểm tra xem camera đã được cắm vào cổng USB chưa)")
    except Exception as cam_err:
        print(f"Lỗi kiểm tra camera: {cam_err}")
        
    print("=" * 60)

if __name__ == "__main__":
    check_env()
