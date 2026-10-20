import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'   # Disable GPU — prevent nvdxgdmal64.dll crash
os.environ['ORT_DIRECTML_DEVICE_ID'] = '-1'
os.environ['TORCH_DEVICE'] = 'cpu'
os.environ['YOLO_AUTOINSTALL'] = 'false'
os.environ['OPENCV_VIDEOIO_PRIORITY_MSMF'] = '0'
os.environ['OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS'] = '0'

import cv2


import numpy as np

import tkinter as tk

from tkinter import ttk, messagebox

from PIL import Image, ImageTk, ImageDraw, ImageFont

import threading

import time

from datetime import datetime

import sys

import traceback

import json

import hashlib

import uuid

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

# Import TFLite interpreter

try:

    import tflite_runtime.interpreter as tflite

    TFLITE_RUNTIME = True

except ImportError:

    try:

        import tensorflow as tf

        TFLITE_RUNTIME = False

        # Chỉ hiện warning khi chạy từ source, không hiện khi chạy EXE

        if not getattr(sys, 'frozen', False):

            print("Using tensorflow.lite (install tflite-runtime for smaller footprint)")

    except ImportError:

        print("Neither tflite-runtime nor tensorflow is installed!")

        sys.exit(1)

# Import PLC control

try:

    import snap7

    PLC_AVAILABLE = True

except ImportError:

    PLC_AVAILABLE = False

    print("snap7 not installed - PLC control disabled")

# Redirect stdout/stderr to file for EXE debugging

if getattr(sys, 'frozen', False):

    log_file = open('app_debug.log', 'w', encoding='utf-8')

    sys.stdout = log_file

    sys.stderr = log_file

# ── Helper: resolve path cho cả source và EXE ──

def _res(filename):

    """Trả về đường dẫn tuyệt đối — hoạt động cả khi chạy .py và .exe"""

    if getattr(sys, 'frozen', False):

        # PyInstaller one-file: file nằm trong thư mục tạm _MEIPASS

        base = sys._MEIPASS

    else:

        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, filename)

def _runtime_path(*parts):

    """Return a writable path beside the EXE, or the project folder in source mode."""

    if getattr(sys, 'frozen', False):

        base = os.path.dirname(sys.executable)

    else:

        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, *parts)

# Configuration

CONFIG = {

    'MODEL_PATH': _res('buiban.h5'),

    'LABELS_PATH': _res('labels_2classes.txt'),

    'PANEL_SEG_MODEL_PATH': _res('panel 2.pt'),

    'IMG_SIZE': (224, 224),            # ← Model mới: 224x224

    'CAMERA_ID': 0,

    'CAMERA_FRAME_WIDTH': 1080,

    'CAMERA_FRAME_HEIGHT': 1920,

    'DISABLE_AUTOFOCUS': True,

    'CAMERA_CONTRAST': 16.0,            # ✅ Cố định độ tương phản camera

    'CAMERA_EXPOSURE': -5.0,            # ✅ Cố định độ phơi sáng camera

    'FRAME_ROTATION_MODE': 'none',

    'FORCE_PORTRAIT_FRAME': True,

    'PORTRAIT_ROTATION': 'ccw',

    'APP_TITLE': 'Hệ Thống Tự Động Vệ Sinh Tấm Pin Mặt Trời',

    'APP_VERSION': '2.4.0-Patch32',     # final version for patch-based pipeline

    # Cleaning triggers - 3 CLASSES: ban / sach / nopanel

    'TRIGGER_CLASS': 'ban',            # ← Kích khi phát hiện "ban"

    'NOPANEL_CLASS': 'nopanel',        # ✅ NEW: Class không có tấm pin

    'MIN_CONFIDENCE': 0.60,            # ✅ NEW: Ngưỡng confidence tối thiểu (60%)

    'CNN_DIRTY_THRESHOLD': 0.05,       # ✅ Ngưỡng quyết định lớp bẩn (tối ưu hóa theo F1-score trên tập validation)

    'TRIGGER_DURATION': 5.0,

    'TRIGGER_COOLDOWN': 5.0,

    'DIRT_AREA_THRESHOLD': 0.06,        # ✅ Tỷ lệ diện tích bẩn tối thiểu để kích hoạt vệ sinh (2/32 patches bẩn)

    'PATCH_ROWS': 8,

    'PATCH_COLS': 4,

    'PATCH_SIZE': 224,

    'PATCH_FRAME_SIZE': (896, 1792),   # (width, height) - portrait temporary resize before ROI+warp

    'MIN_VALID_PATCHES': 10,

    # Keep CNN input close to the training/test distribution. YOLO-Seg should
    # locate the panel, but perspective-warping/masking can erase subtle dirt.
    'USE_PANEL_PERSPECTIVE_WARP': True,
    'MASK_BACKGROUND_FOR_CNN': False,
    'PANEL_CROP_PADDING': 0.02,

    # Snapshot mode settings

    'SNAPSHOT_MODE': True,             # ✅ NEW: True = chụp ảnh định kỳ, False = video liên tục

    'SNAPSHOT_INTERVAL': 600,          # ✅ NEW: Chu kỳ chụp ảnh (600s = 10 phút)

    'SAVE_SNAPSHOTS': True,            # ✅ NEW: Lưu ảnh đã chụp

    'SNAPSHOT_FOLDER': _runtime_path('snapshots'),

    'SAVE_PATCH_IMAGES': True,         # Lưu 32 ảnh patch để phục vụ train lại sau này

    'PATCH_IMAGE_FOLDER': _runtime_path('anh_32_patch'),

    # PLC settings

    'PLC': {

        'ENABLED': True,

        'IP': '192.168.0.1',

        'RACK': 0,

        'SLOT': 1,

        'DB_NUMBER': 1,

        'DB_START': 0,

        'DB_SIZE': 18,              # Mở rộng: 1 byte fault + 1 pad + 4 REAL (PZEM-017)

        'POWER_OFFSET': 2,          # Byte bắt đầu dữ liệu PZEM-017 trong DB1

    },

    # PZEM-017 Power Monitoring (đọc trực tiếp qua USB)

    'PZEM_PORT': 'AUTO',                # COM port (VD: 'COM3') hoặc 'AUTO' để tự tìm

    'POWER_READ_INTERVAL': 2,       # Đọc mỗi 2 giây (giúp đáp ứng nhanh hơn)

    'POWER_AVG_WINDOW': 300,        # 5 phút trung bình

    'POST_CLEAN_DELAY': 60,         # Đợi 60 giây sau vệ sinh để đo hiệu suất

    # Authentication

    'AUTH_USERNAME': 'admin',

    'AUTH_PASSWORD': 'admin',

    # ☁️ Cloud API (push data lên cloud server)

    'CLOUD_ENABLED': False,              # Bật/tắt cloud sync

    'CLOUD_URL': 'http://localhost:8000', # URL cloud server

    'CLOUD_API_KEY': 'solar-device-key-change-me',

    'CLOUD_DEVICE_ID': 'device-001',

    'CLOUD_PUSH_INTERVAL': 2,            # Push status mỗi 2 giây

    'CLOUD_FRAME_INTERVAL': 3,           # Push frame mỗi 3 giây

}

def apply_frame_rotation(frame, config):

    """Normalize camera orientation using an explicit rotation mode."""

    if frame is None:

        return frame

    mode = str(config.get('FRAME_ROTATION_MODE', '')).strip().lower()

    if not mode:

        if config.get('FORCE_PORTRAIT_FRAME', False):

            legacy_rotation = str(config.get('PORTRAIT_ROTATION', 'ccw')).strip().lower()

            mode = f'auto_{legacy_rotation}'

        else:

            mode = 'none'

    height, width = frame.shape[:2]

    if mode in ('none', 'off'):

        return frame

    if mode == 'cw':

        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

    if mode == 'ccw':

        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

    if mode == '180':

        return cv2.rotate(frame, cv2.ROTATE_180)

    if mode == 'auto_cw':

        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE) if width > height else frame

    if mode == 'auto_ccw':

        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE) if width > height else frame

    return frame

class PLCController:

    """Điều khiển PLC Siemens S7"""

    def __init__(self, config):

        self.config = config['PLC']

        self.client = None

        self.is_connected = False

        self.last_trigger_time = 0

    def connect(self):

        """Kết nối tới PLC"""

        if not PLC_AVAILABLE:

            print("❌ snap7 library not available")

            return False

        try:

            self.client = snap7.client.Client()

            self.client.connect(

                self.config['IP'],

                self.config['RACK'],

                self.config['SLOT']

            )

            self.is_connected = self.client.get_connected()

            if self.is_connected:

                print(f"✅ PLC Connected: {self.config['IP']}")

            else:

                print(f"❌ PLC Connection failed")

            return self.is_connected

        except Exception as e:

            print(f"❌ PLC Connection error: {e}")

            self.is_connected = False

            return False

    def disconnect(self):

        """Ngắt kết nối PLC"""

        if self.client:

            try:

                self.client.disconnect()

                print("PLC disconnected")

            except:

                pass

        self.is_connected = False

    def trigger_faults(self, has_dirt=False, has_leaf=False, has_bird_drop=False):

        """Kích PLC tùy theo loại lỗi phát hiện (Bụi: DBX0.0, Lá: DBX0.1, Phân chim: DBX0.2)"""

        if not self.is_connected:

            print("⚠️  PLC not connected - cannot trigger")

            return False

        current_time = time.time()

        if current_time - self.last_trigger_time < CONFIG['TRIGGER_COOLDOWN']:

            print(f"⏳ Cooldown active ({CONFIG['TRIGGER_COOLDOWN']}s)")

            return False

        mask = 0x00

        if has_dirt: mask |= 0x01       # DBX0.0

        if has_leaf: mask |= 0x02       # DBX0.1

        if has_bird_drop: mask |= 0x04  # DBX0.2

        if mask == 0:

            return False

        try:

            # Chỉ đọc/ghi 1 byte fault (offset 0) — không đụng vào vùng power (offset 2-17)

            data = bytearray(self.client.db_read(

                self.config['DB_NUMBER'],

                self.config['DB_START'],

                1  # Chỉ 1 byte fault bits

            ))

            data[0] |= mask

            self.client.db_write(

                self.config['DB_NUMBER'],

                self.config['DB_START'],

                data

            )

            logs = []

            if has_dirt: logs.append("DBX0.0=1 (Bụi)")

            if has_leaf: logs.append("DBX0.1=1 (Lá cây)")

            if has_bird_drop: logs.append("DBX0.2=1 (Phân chim)")

            print(f"🔌 PLC → DB{self.config['DB_NUMBER']}.DBX{self.config['DB_START']} | {', '.join(logs)}")

            time.sleep(1.0)

            data[0] &= (~mask & 0xFF)

            self.client.db_write(

                self.config['DB_NUMBER'],

                self.config['DB_START'],

                data

            )

            print(f"🔌 PLC → Đã Reset các bit về 0")

            self.last_trigger_time = current_time

            return True

        except Exception as e:

            print(f"❌ PLC trigger error: {e}")

            traceback.print_exc()

            return False

    def trigger_cleaning(self):

        """Kích PLC mặc định (bụi) - Dùng cho nút bấm Manual"""

        return self.trigger_faults(has_dirt=True)

    def read_power(self):

        """Đọc dữ liệu PZEM-017 từ DB1 offset 2-17 (4 x REAL)."""

        if not self.is_connected or not self.client:

            return None

        try:

            import struct as _st

            data = self.client.db_read(self.config['DB_NUMBER'], 2, 16)

            voltage = _st.unpack('>f', data[0:4])[0]

            current = _st.unpack('>f', data[4:8])[0]

            power   = _st.unpack('>f', data[8:12])[0]

            energy  = _st.unpack('>f', data[12:16])[0]

            return {

                'voltage': round(voltage, 2),

                'current': round(current, 3),

                'power': round(power, 1),

                'energy': round(energy, 3),

            }

        except Exception as e:

            print(f"❌ PLC read_power error: {e}")

            return None

class DirtDetectorTFLite:

    """

    """

    def __init__(self, config):

        self.config = config

        self.interpreter = None

        self.input_details = None

        self.output_details = None

        self.labels = None

        self.batch_supported = False

        self.patch_rows = int(self.config.get('PATCH_ROWS', 4))

        self.patch_cols = int(self.config.get('PATCH_COLS', 8))

        self.patch_size = int(self.config.get('PATCH_SIZE', 224))

        self.total_patches = self.patch_rows * self.patch_cols

        self.clean_index = None

        self.dirty_index = None

        self.nopanel_index = None

        self._next_patch_image_index = None

        self.last_saved_patch_dir = None

        self.predict_lock = threading.Lock()  # Lock để bảo vệ interpreter

    def load_model(self):

        """Load Keras model weights/model (.h5) dynamically, fallback to EfficientNetB0 if load_weights is strictly needed."""

        try:

            import tensorflow as tf

            tf.get_logger().setLevel('ERROR')

            # Force CPU-only execution to avoid BLAS/cuBLAS StreamExecutor errors

            tf.config.set_visible_devices([], 'GPU')

            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

            model_path = self.config['MODEL_PATH']

            print(f"Đang tải model từ: {model_path} ...")

            try:

                # Thử load toàn bộ model trực tiếp bằng tf.keras.models.load_model

                self.model = tf.keras.models.load_model(model_path)

                print(f"[OK] Đã tải thành công toàn bộ model từ: {model_path}")

            except Exception as load_err:

                print(f"Không thể load_model trực tiếp ({load_err}). Thử dựng lại kiến trúc và nạp trọng số...")

                from tensorflow.keras import layers

                from tensorflow.keras.applications import EfficientNetB0

                # Dựng lại kiến trúc giống hệt script test cũ (EfficientNetB0)

                data_augmentation = tf.keras.Sequential([

                    layers.RandomFlip("horizontal_and_vertical"),

                    layers.RandomRotation(0.2),

                ], name="sequential")

                base_model = EfficientNetB0(input_shape=(self.patch_size, self.patch_size, 3), 

                                            include_top=False, 

                                            weights=None)

                base_model._name = "functional"

                inputs = tf.keras.Input(shape=(self.patch_size, self.patch_size, 3))

                x = data_augmentation(inputs)

                x = base_model(x, training=False)

                x = layers.GlobalAveragePooling2D(name="global_average_pooling2d")(x)

                x = layers.Dropout(0.2, name="dropout")(x)

                outputs = layers.Dense(2, activation='softmax', name="dense")(x)

                self.model = tf.keras.Model(inputs, outputs)

                try:

                    self.model.load_weights(model_path)

                    print(f"[OK] Đã dựng kiến trúc EfficientNetB0 và tải trọng số thành công.")

                except Exception as load_w_err:

                    print(f"Không thể tải trọng số trực tiếp ({load_w_err}). Thử ánh xạ trọng số Keras 3 thủ công...")

                    try:

                        import h5py

                        # Ánh xạ thủ công từ cấu trúc Keras 3 sang model Keras 2

                        with h5py.File(model_path, 'r') as f_h5:

                            # 1. Nạp trọng số Dense

                            dense_w = []

                            if 'dense' in f_h5['layers'] and 'vars' in f_h5['layers']['dense']:

                                dense_w = [np.array(f_h5['layers']['dense']['vars'][str(i)]) for i in range(len(f_h5['layers']['dense']['vars']))]

                            if dense_w:

                                self.model.get_layer('dense').set_weights(dense_w)

                                

                            # 2. Phân loại và sắp xếp các lớp Keras 3 trong functional

                            h5_funcs = f_h5['layers']['functional']['layers']

                            def get_layer_sort_key(name):

                                if '_' in name:

                                    parts = name.split('_')

                                    if parts[-1].isdigit():

                                        idx = int(parts[-1])

                                        type_str = '_'.join(parts[:-1])

                                        return (type_str, idx)

                                return (name, 0)

                                

                            from collections import defaultdict

                            layers_by_type = defaultdict(list)

                            for name in h5_funcs.keys():

                                g = h5_funcs[name]

                                if 'vars' in g and len(g['vars']) > 0:

                                    type_str, idx = get_layer_sort_key(name)

                                    w_list = [np.array(g['vars'][str(i)]) for i in range(len(g['vars']))]

                                    layers_by_type[type_str].append((idx, name, w_list))

                                    

                            for type_str in layers_by_type:

                                layers_by_type[type_str].sort(key=lambda x: x[0])

                                

                            # 3. Phân loại các lớp có trọng số của Keras 2 model

                            k2_layers_by_type = defaultdict(list)

                            for layer in base_model.layers:

                                if layer.weights:

                                    cls_name = type(layer).__name__.lower()

                                    t_key = cls_name

                                    if cls_name == 'conv2d':

                                        t_key = 'conv2d'

                                    elif cls_name == 'depthwiseconv2d':

                                        t_key = 'depthwise_conv2d'

                                    elif cls_name == 'batchnormalization':

                                        t_key = 'batch_normalization'

                                    k2_layers_by_type[t_key].append(layer)

                                    

                            # 4. Thiết lập trọng số theo thứ tự tuần tự

                            for t_key in k2_layers_by_type:

                                k2_lst = k2_layers_by_type[t_key]

                                h5_lst = layers_by_type[t_key]

                                for k2_layer, h5_item in zip(k2_lst, h5_lst):

                                    _, _, h5_w = h5_item

                                    k2_layer.set_weights(h5_w)

                        print(f"[OK] Đã ánh xạ thành công các trọng số Keras 3 sang cấu trúc model Keras 2.")

                    except Exception as map_err:

                        print(f"[ERROR] Thất bại khi ánh xạ trọng số thủ công: {map_err}")

                        import traceback

                        traceback.print_exc()

                        return False

            self.batch_supported = True

            print("Đang khởi động (warm-up) Keras model...")

            dummy_input = np.zeros((1, self.patch_size, self.patch_size, 3), dtype=np.float32)

            self.model.predict(dummy_input, verbose=0)

            return True

        except Exception as e:

            print(f"[ERROR] Model loading error: {e}")

            import traceback

            traceback.print_exc()

            return False

    def load_labels(self):

        """Load labels"""

        try:

            with open(self.config['LABELS_PATH'], 'r', encoding='utf-8') as f:

                self.labels = [ln.strip().split(' ', 1)[-1] 

                             for ln in f if ln.strip()]

            print(f"[OK] Labels loaded: {self.labels}")

            return True

        except Exception as e:

            print(f"[ERROR] Labels loading error: {e}")

            return False

    def _find_label_index(self, keywords):

        if not self.labels:

            return None

        for i, label in enumerate(self.labels):

            label_lower = label.lower()

            if any(keyword in label_lower for keyword in keywords):

                return i

        return None

    def _label_for_index(self, index, fallback):

        if self.labels is not None and index is not None and 0 <= index < len(self.labels):

            return self.labels[index]

        return fallback

    def preprocess_patch(self, frame):

        """Preprocess a single patch for Keras EfficientNetB0 — input là RGB uint8 (0-255)."""

        # Resize về kích thước model nếu cần

        h, w = frame.shape[:2]

        target = self.config['IMG_SIZE']

        if (w, h) != target:

            frame = cv2.resize(frame, target, interpolation=cv2.INTER_LINEAR)

        # BGR → RGB (EfficientNetB0 nhận RGB)

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Trả về float32 dạng 0-255 (EfficientNetB0 tự normalize bên trong)

        return img.astype(np.float32)

    def _order_points(self, pts):

        """Order 4 points: top-left, top-right, bottom-right, bottom-left."""

        rect = np.zeros((4, 2), dtype="float32")

        s = pts.sum(axis=1)

        rect[0] = pts[np.argmin(s)] # top-left

        rect[2] = pts[np.argmax(s)] # bottom-right

        diff = np.diff(pts, axis=1)

        rect[1] = pts[np.argmin(diff)] # top-right

        rect[3] = pts[np.argmax(diff)] # bottom-left

        return rect

    def _get_panel_corners(self, mask):

        """Extract 4 corners from a binary mask using polygon approximation."""

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:

            return None

        # Lấy contour lớn nhất

        cnt = max(contours, key=cv2.contourArea)

        # Xấp xỉ đa giác

        epsilon = 0.05 * cv2.arcLength(cnt, True)

        approx = cv2.approxPolyDP(cnt, epsilon, True)

        if len(approx) == 4:

            return approx.reshape(4, 2)

        else:

            # Nếu không tìm được đúng 4 góc, dùng rect xoay tối thiểu (rotated bbox)

            rect = cv2.minAreaRect(cnt)

            box = cv2.boxPoints(rect)

            return np.int0(box)

    def prepare_panel_frame(self, frame, mask=None):

        """

        Prepare panel frame using Perspective Warp if mask is provided, 

        otherwise fallback to simple resize.

        """

        target_w, target_h = self.config.get('PATCH_FRAME_SIZE', (896, 1792))

        if mask is not None and np.sum(mask) > 0:

            corners = self._get_panel_corners(mask)

            if corners is not None:

                # Nắn thẳng tấm pin bằng Perspective Transform

                rect = self._order_points(corners)

                # Tính toán khoảng cách cạnh để xác định chiều tấm pin (Dọc hay Ngang)
                w1 = np.linalg.norm(rect[0] - rect[1])
                w2 = np.linalg.norm(rect[2] - rect[3])
                h1 = np.linalg.norm(rect[0] - rect[3])
                h2 = np.linalg.norm(rect[1] - rect[2])

                avg_width = (w1 + w2) / 2
                avg_height = (h1 + h2) / 2

                if avg_width > avg_height:
                    # Tấm pin nằm ngang (Landscape)
                    target_w, target_h = 1792, 896
                    self.patch_rows = 4
                    self.patch_cols = 8
                    print(f"📐 Phát hiện tấm pin nằm ngang (Landscape) -> Đặt kích thước {target_w}x{target_h}, lưới 4x8")
                else:
                    # Tấm pin nằm dọc (Portrait)
                    target_w, target_h = 896, 1792
                    self.patch_rows = 8
                    self.patch_cols = 4
                    print(f"📐 Phát hiện tấm pin nằm dọc (Portrait) -> Đặt kích thước {target_w}x{target_h}, lưới 8x4")

                self.total_patches = self.patch_rows * self.patch_cols

                dst = np.array([

                    [0, 0],

                    [target_w - 1, 0],

                    [target_w - 1, target_h - 1],

                    [0, target_h - 1]

                ], dtype="float32")

                M = cv2.getPerspectiveTransform(rect, dst)

                warped = cv2.warpPerspective(frame, M, (target_w, target_h))

                return warped

        # Fallback: Resize thông thường
        h_f, w_f = frame.shape[:2]
        if w_f > h_f:
            target_w, target_h = 1792, 896
            self.patch_rows = 4
            self.patch_cols = 8
        else:
            target_w, target_h = 896, 1792
            self.patch_rows = 8
            self.patch_cols = 4
        self.total_patches = self.patch_rows * self.patch_cols

        return cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    def extract_patch_batch(self, frame, mask=None):

        """Prepare panel frame (warp/resize) then split into 32 patches."""

        panel_frame = self.prepare_panel_frame(frame, mask)

        patches = []

        boxes = []

        raw_patches = []

        for row in range(self.patch_rows):

            for col in range(self.patch_cols):

                x1 = col * self.patch_size

                y1 = row * self.patch_size

                x2 = x1 + self.patch_size

                y2 = y1 + self.patch_size

                patch = panel_frame[y1:y2, x1:x2]

                raw_patches.append(patch.copy())

                patches.append(self.preprocess_patch(patch))

                boxes.append((x1, y1, x2, y2))

        return panel_frame, np.stack(patches, axis=0).astype(np.float32), boxes, raw_patches

    def _run_patch_inference(self, patch_batch):

        """Run the Keras classifier on all patches using batch mode."""

        with self.predict_lock:

            # Keras model.predict natively supports batching

            outputs = self.model.predict(patch_batch, verbose=0)

        return outputs

    def draw_text_pil(self, img, text, pos, font_size=30, color=(255, 255, 255), bold=False):

        """Draw high-quality text using PIL (supports custom fonts and better rendering)"""

        try:

            # Chuyển OpenCV (BGR) sang PIL (RGB)

            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            draw = ImageDraw.Draw(img_pil)

            # Thử tải font hệ thống (Windows)

            font_names = ["segoeuib.ttf" if bold else "segoeui.ttf", "arial.ttf"]

            font = None

            for f_name in font_names:

                try:

                    font = ImageFont.truetype(f_name, font_size)

                    break

                except:

                    continue

            if font is None:

                font = ImageFont.load_default()

            # Vẽ chữ

            draw.text(pos, text, font=font, fill=color[::-1]) # PIL dùng RGB

            # Chuyển lại sang OpenCV (BGR)

            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

        except Exception as e:

            # Fallback về OpenCV gốc nếu lỗi

            cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            return img

    def _build_debug_frame(self, panel_frame, patch_results, dirty_ratio, valid_count, min_valid, dirty_count):

        """Create a patch-grid visualization for the snapshot UI."""

        disp = panel_frame.copy()

        for patch in patch_results:

            x1, y1, x2, y2 = patch['box']

            state = patch['state']

            if state == 'dirty':

                color = (0, 0, 255)

                # Vẽ lớp phủ đỏ nhạt (semi-transparent red overlay)

                overlay = disp.copy()

                cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1) # Tô màu đỏ đặc

                alpha = 0.25 # Độ trong suốt của màu đỏ nhạt

                cv2.addWeighted(overlay, alpha, disp, 1 - alpha, 0, disp)

            elif state == 'clean':

                color = (0, 200, 0)

            elif state == 'noise':

                color = (0, 215, 255)   # Vàng — nhiễu, bị bỏ qua

            else:

                color = (0, 165, 255)

            # Vẽ đường viền cho ô

            cv2.rectangle(disp, (x1, y1), (x2, y2), color, 2)

        # Vẽ khung viền tổng quát cho ảnh CNN

        cv2.rectangle(disp, (0, 0), (disp.shape[1], disp.shape[0]), (255, 255, 255), 2)

        return disp

    def _get_next_patch_image_index(self):

        """Return the next global patch image index based on files already saved."""

        if self._next_patch_image_index is not None:

            return self._next_patch_image_index

        patch_root = self.config.get('PATCH_IMAGE_FOLDER', _runtime_path('anh_32_patch'))

        os.makedirs(patch_root, exist_ok=True)

        max_index = 0

        for filename in os.listdir(patch_root):

            stem, ext = os.path.splitext(filename)

            if ext.lower() not in ('.jpg', '.jpeg', '.png'):

                continue

            if stem.isdigit():

                max_index = max(max_index, int(stem))

        self._next_patch_image_index = max_index + 1

        return self._next_patch_image_index

    def _save_patch_images(self, raw_patches):

        """Save the 32 panel patches with continuous numbering for future retraining."""

        if not self.config.get('SAVE_PATCH_IMAGES', True):

            return None

        if not raw_patches:

            return None

        patch_root = self.config.get('PATCH_IMAGE_FOLDER', _runtime_path('anh_32_patch'))

        os.makedirs(patch_root, exist_ok=True)

        next_index = self._get_next_patch_image_index()

        saved_paths = []

        for patch in raw_patches:

            if patch is None or patch.size == 0:

                continue

            patch_path = os.path.join(patch_root, f"{next_index}.jpg")

            cv2.imwrite(patch_path, patch)

            saved_paths.append(patch_path)

            next_index += 1

        self._next_patch_image_index = next_index

        self.last_saved_patch_dir = patch_root

        if saved_paths:

            print(f"💾 Da luu {len(saved_paths)} anh patch: {saved_paths[0]} -> {saved_paths[-1]}")

        return patch_root

    def predict(self, frame, mask=None):

        """

        Patch-based prediction for 2 classes (sach, ban).

        Accepts optional mask for Perspective Warping.

        """

        if self.clean_index is None:

            self.clean_index = self._find_label_index(('sach', 'clean'))

        if self.dirty_index is None:

            self.dirty_index = self._find_label_index(('ban', 'dirty'))

        panel_frame, patch_batch, patch_boxes, raw_patches = self.extract_patch_batch(frame, mask)

        if self.config.get('SAVE_PATCH_IMAGES', True):

            self._save_patch_images(raw_patches)

        patch_outputs = self._run_patch_inference(patch_batch)

        min_confidence = float(self.config.get('MIN_CONFIDENCE', 0.60))

        cnn_dirty_threshold = float(self.config.get('CNN_DIRTY_THRESHOLD', 0.65))

        min_valid_patches = int(self.config.get('MIN_VALID_PATCHES', 10))

        dirty_count = 0

        clean_count = 0

        dirty_confidences = []

        clean_confidences = []

        patch_results = []

        dirty_idx = self.dirty_index if self.dirty_index is not None else 1

        clean_idx = self.clean_index if self.clean_index is not None else 0

        for probs, box in zip(patch_outputs, patch_boxes):

            # Xác định xác suất của lớp bẩn
            prob_dirty = float(probs[dirty_idx]) if len(probs) > dirty_idx else 0.0

            # Thay vì argmax (0.5), sử dụng cnn_dirty_threshold
            if prob_dirty >= cnn_dirty_threshold:

                pred_index = dirty_idx

                confidence = prob_dirty

            else:

                pred_index = clean_idx

                confidence = float(probs[clean_idx]) if len(probs) > clean_idx else (1.0 - prob_dirty)

            label_name = self._label_for_index(pred_index, f"Class {pred_index}")

            if self.dirty_index is not None and pred_index == self.dirty_index:

                state = 'dirty'

                dirty_count += 1

                dirty_confidences.append(confidence)

                short_label = 'D'

            elif self.clean_index is not None and pred_index == self.clean_index:

                state = 'clean'

                clean_count += 1

                clean_confidences.append(confidence)

                short_label = 'C'

            else:

                state = 'uncertain'

                short_label = '?'

            patch_results.append({

                'box': box,

                'label_name': label_name,

                'confidence': confidence,

                'state': state,

                'short_label': short_label,

            })

        valid_count = self.total_patches

        dirty_ratio = (dirty_count / valid_count) if valid_count else 0.0

        clean_ratio = (clean_count / valid_count) if valid_count else 0.0

        # ── Noise suppression ──────────────────────────────────────────────

        # Vụi bẩn thực tế luôn lan theo mảng (≥ 2 ô liền kề bị bẩn).

        # Đã VÔ HIỆU HÓA theo yêu cầu: Bỏ qua cơ chế báo động giả để đoán gì ghi nấy.

        USE_NOISE_SUPPRESSION = False

        if USE_NOISE_SUPPRESSION:

            MIN_DIRTY_PATCHES = 2

            if dirty_count < MIN_DIRTY_PATCHES:

                dirty_ratio = 0.0

                dirty_confidences = []

                dirty_count = 0

                # Đánh dấu lại các ô nhiễu để hiển thị màu khác trên debug frame

                for p in patch_results:

                    if p['state'] == 'dirty':

                        p['state'] = 'noise'

                        p['short_label'] = 'N'

        # ──────────────────────────────────────────────────────────────────

        if dirty_count > 0 and dirty_ratio >= clean_ratio:

            predicted_class = self.dirty_index if self.dirty_index is not None else 1

            label_name = self._label_for_index(predicted_class, self.config.get('TRIGGER_CLASS', 'ban'))

            confidence = float(np.mean(dirty_confidences)) if dirty_confidences else dirty_ratio

        else:

            predicted_class = self.clean_index if self.clean_index is not None else 0

            label_name = self._label_for_index(predicted_class, 'sach')

            confidence = float(np.mean(clean_confidences)) if clean_confidences else max(0.0, 1.0 - dirty_ratio)

        pred_probs = np.array([clean_ratio, dirty_ratio], dtype=np.float32)

        debug_frame = self._build_debug_frame(

            panel_frame,

            patch_results,

            dirty_ratio,

            valid_count,

            min_valid_patches,

            dirty_count,

        )

        self.last_analysis = {

            'panel_frame': panel_frame,

            'debug_frame': debug_frame,

            'p_dirty': float(dirty_ratio),

            'dirty_ratio': float(dirty_ratio),

            'predicted_class': int(predicted_class),

            'label_name': label_name,

            'pred_probs': pred_probs,

            'confidence': float(confidence),

            'dirty_patch_count': int(dirty_count),

            'clean_patch_count': int(clean_count),

            'nopanel_patch_count': 0,

            'valid_patch_count': int(valid_count),

            'panel_coverage': 1.0,

            'patch_results': patch_results,

            'patch_outputs': patch_outputs,

        }

        return (

            self.last_analysis['p_dirty'],

            self.last_analysis['predicted_class'],

            self.last_analysis['label_name'],

            self.last_analysis['pred_probs'],

            self.last_analysis['confidence'],

        )

    def compute_dirt_ratio(self, frame):

        """

        Compatibility wrapper for the old pipeline.

        Returns the semantic dirty patch ratio plus the patch-grid visualization frame.

        """

        if not hasattr(self, 'last_analysis'):

            self.predict(frame)

        dirty_ratio = float(self.last_analysis.get('dirty_ratio', 0.0))

        debug_frame = self.last_analysis.get('debug_frame')

        if debug_frame is None:

            debug_frame = self.prepare_panel_frame(frame)

        return dirty_ratio, debug_frame

def cleanup_old_snapshots(folder_path, max_size_gb=1.0):

    """

    Xóa ảnh cũ nhất khi thư mục vượt quá kích thước cho phép

    Args:

        folder_path: Đường dẫn thư mục snapshots

        max_size_gb: Kích thước tối đa (GB), mặc định 1GB

    """

    try:

        if not os.path.exists(folder_path):

            return

        # Tính tổng kích thước thư mục

        total_size = 0

        file_list = []

        for filename in os.listdir(folder_path):

            filepath = os.path.join(folder_path, filename)

            if os.path.isfile(filepath) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):

                file_size = os.path.getsize(filepath)

                file_mtime = os.path.getmtime(filepath)

                total_size += file_size

                file_list.append((filepath, file_mtime, file_size))

        # Chuyển đổi sang GB

        total_size_gb = total_size / (1024 ** 3)

        # Nếu vượt quá giới hạn, xóa ảnh cũ nhất

        if total_size_gb > max_size_gb:

            print(f"⚠️ Thư mục snapshots đạt {total_size_gb:.2f}GB (giới hạn {max_size_gb}GB)")

            # Sắp xếp theo thời gian (cÅ© nhất trước)

            file_list.sort(key=lambda x: x[1])

            deleted_count = 0

            deleted_size = 0

            # Xóa ảnh cũ cho đến khi xuống dưới 80% giới hạn

            target_size_gb = max_size_gb * 0.8

            for filepath, mtime, fsize in file_list:

                if total_size_gb <= target_size_gb:

                    break

                try:

                    os.remove(filepath)

                    total_size_gb -= fsize / (1024 ** 3)

                    deleted_size += fsize

                    deleted_count += 1

                    print(f"🗑️ Đã xóa: {os.path.basename(filepath)}")

                except Exception as e:

                    print(f"❌ Lỗi xóa {filepath}: {e}")

            if deleted_count > 0:

                print(f"✅ Đã xóa {deleted_count} ảnh cũ ({deleted_size / (1024**2):.1f}MB)")

                print(f"📊 Dung lượng còn lại: {total_size_gb:.2f}GB")

    except Exception as e:

        print(f"❌ Lỗi cleanup snapshots: {e}")

# ==================== VIRTUAL KEYBOARD (Touch HMI) ====================

class VirtualKeyboard:

    """Bàn phím ảo QWERTY cho màn hình cảm ứng HMI — SCADA dark theme"""

    _instance = None   # Singleton — chỉ 1 keyboard tại 1 thời điểm

    @classmethod

    def show(cls, root, target_entry, is_password=False, on_confirm=None):

        """Hiện bàn phím cho entry đang focus"""

        if cls._instance:

            cls._instance.dismiss()

        cls._instance = cls(root, target_entry, is_password, on_confirm)

    def __init__(self, root, target_entry, is_password=False, on_confirm=None):

        self.root = root

        self.target = target_entry

        self.is_password = is_password

        self.on_confirm = on_confirm

        self.shift_on = False

        self.caps_on = False

        self.key_buttons = []  # FIX: Khởi tạo TRƯỚC khi tạo phím

        self._raw_text = target_entry.get()  # FIX: Lưu text gốc riêng biệt

        # Colors

        BG = '#0d1117'

        KEY_BG = '#1e293b'

        KEY_FG = '#e2e8f0'

        SPEC_BG = '#334155'

        ENTER_BG = '#3b82f6'

        DEL_BG = '#ef4444'

        # Overlay nền mờ

        self.overlay = tk.Frame(root, bg='#000000')

        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)

        self.overlay.configure(bg=BG)

        self.overlay.bind('<Button-1>', lambda e: None)  # Chặn click xuyên

        # Dismiss button (X) ở góc phải trên — lớn cho HMI

        dismiss_btn = tk.Button(

            self.overlay, text='✖  Đóng', font=('Segoe UI Semibold', 16),

            bg='#64748b', fg='white', activebackground='#475569',

            relief=tk.FLAT, bd=0, padx=16, pady=6, cursor='hand2',

            command=self.dismiss

        )

        dismiss_btn.place(relx=1.0, rely=0.0, anchor='ne', x=-10, y=10)

        # Keyboard panel ở phía dưới

        self.panel = tk.Frame(self.overlay, bg=BG)

        self.panel.place(relx=0.5, rely=1.0, anchor='s', relwidth=1)

        # Hiện giá trị đang nhập (preview)

        preview_frame = tk.Frame(self.panel, bg='#172030')

        preview_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        display_text = '•' * len(self._raw_text) if is_password else self._raw_text

        self.preview_label = tk.Label(

            preview_frame, text=display_text,

            font=('Consolas', 26, 'bold'), bg='#172030', fg='#00ff88',

            anchor='w', padx=20, pady=12

        )

        self.preview_label.pack(fill=tk.X)

        # Cursor nhấp nháy

        self._cursor_visible = True

        self._blink_cursor()

        # Các hàng phím

        rows = [

            ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],

            ['!', '@', '#', '$', '%', '&', '*', '-', '_', '+'],

            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],

            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],

            ['z', 'x', 'c', 'v', 'b', 'n', 'm'],

        ]

        # Row 1: numbers

        self._make_row(rows[0], KEY_BG, KEY_FG)

        # Row 2: special characters (cho mật khẩu mạnh)

        self._make_row(rows[1], '#2d3748', '#fbbf24')

        # Row 3: qwerty

        self._make_row(rows[2], KEY_BG, KEY_FG)

        # Row 4: asdf with shift+backspace

        row4 = tk.Frame(self.panel, bg=BG)

        row4.pack(pady=2)

        self._make_key(row4, '⇧', SPEC_BG, '#fbbf24', width=6, command=self._toggle_shift)

        for k in rows[3]:

            self._make_key(row4, k, KEY_BG, KEY_FG)

        self._make_key(row4, '⌫', DEL_BG, 'white', width=6, command=self._backspace)

        # Row 5: zxcv

        row5 = tk.Frame(self.panel, bg=BG)

        row5.pack(pady=2)

        self._make_key(row5, 'CAPS', SPEC_BG, '#fbbf24', width=6, command=self._toggle_caps)

        for k in rows[4]:

            self._make_key(row5, k, KEY_BG, KEY_FG)

        self._make_key(row5, '.', KEY_BG, KEY_FG)

        self._make_key(row5, '/', KEY_BG, KEY_FG)

        # Row 6: space + special

        row6 = tk.Frame(self.panel, bg=BG)

        row6.pack(pady=(2, 10))

        self._make_key(row6, 'Clear', SPEC_BG, '#fbbf24', width=8, command=self._clear)

        self._make_key(row6, 'SPACE', KEY_BG, KEY_FG, width=22, command=lambda: self._type(' '))

        self._make_key(row6, '✔ OK', ENTER_BG, 'white', width=10, command=self._confirm)

        self.overlay.lift()

    def _make_row(self, keys, bg, fg):

        row = tk.Frame(self.panel, bg='#0d1117')

        row.pack(pady=3)

        for k in keys:

            self._make_key(row, k, bg, fg)

    def _make_key(self, parent, text, bg, fg, width=4, command=None):

        def _flash_reset(b, orig_bg):

            try:

                b.config(bg=orig_bg)

            except Exception:

                pass  # Widget có thể đã bị destroy (VD: nhấn OK)

        def on_press(b, orig_bg, cmd):

            """Visual feedback khi nhấn phím trên HMI"""

            b.config(bg='#3b82f6')

            self.root.after(100, lambda: _flash_reset(b, orig_bg))

            if cmd:

                cmd()

            else:

                self._type(text)

        btn = tk.Button(

            parent, text=text, font=('Segoe UI', 18, 'bold'),

            bg=bg, fg=fg, activebackground='#3b82f6', activeforeground='white',

            relief=tk.FLAT, bd=0, width=width, height=1,

            cursor='hand2',

        )

        btn.config(command=lambda b=btn, obg=bg, c=command: on_press(b, obg, c))

        btn.pack(side=tk.LEFT, padx=3, pady=2, ipady=14)

        if len(text) == 1 and text.isalpha():

            self.key_buttons.append((btn, text))

        return btn

    def _type(self, char):

        if self.shift_on or self.caps_on:

            char = char.upper()

            if self.shift_on and not self.caps_on:

                self.shift_on = False

                self._update_key_labels()

        self._raw_text += char

        self.target.delete(0, tk.END)

        self.target.insert(0, self._raw_text)

        self._update_preview()

    def _backspace(self):

        if self._raw_text:

            self._raw_text = self._raw_text[:-1]

            self.target.delete(0, tk.END)

            self.target.insert(0, self._raw_text)

            self._update_preview()

    def _clear(self):

        self._raw_text = ''

        self.target.delete(0, tk.END)

        self._update_preview()

    def _toggle_shift(self):

        self.shift_on = not self.shift_on

        self._update_key_labels()

    def _toggle_caps(self):

        self.caps_on = not self.caps_on

        self._update_key_labels()

    def _update_key_labels(self):

        upper = self.shift_on or self.caps_on

        for btn, original in self.key_buttons:

            btn.config(text=original.upper() if upper else original)

    def _update_preview(self):

        if self.is_password:

            self.preview_label.config(text='•' * len(self._raw_text))

        else:

            self.preview_label.config(text=self._raw_text)

    def _blink_cursor(self):

        """FIX: Sử dụng _raw_text riêng biệt — không bị lỗi khi text chứa '|'"""

        try:

            if not self.overlay.winfo_exists():

                return

            if self.is_password:

                base = '•' * len(self._raw_text)

            else:

                base = self._raw_text

            if self._cursor_visible:

                self.preview_label.config(text=base + '|')

            else:

                self.preview_label.config(text=base)

            self._cursor_visible = not self._cursor_visible

            self.root.after(500, self._blink_cursor)

        except Exception:

            pass

    def _confirm(self):

        callback = self.on_confirm

        self.dismiss()

        if callback:

            self.root.after(50, callback)

    def dismiss(self):

        VirtualKeyboard._instance = None

        try:

            self.overlay.destroy()

        except Exception:

            pass

class VirtualNumpad:

    """Bàn phím số cho màn hình cảm ứng HMI — nhập thông số"""

    _instance = None

    @classmethod

    def show(cls, root, target_entry, on_apply=None, title='Nhập giá trị', unit='', min_val=None, max_val=None):

        if cls._instance:

            cls._instance.dismiss()

        cls._instance = cls(root, target_entry, on_apply, title, unit, min_val, max_val)

    def __init__(self, root, target_entry, on_apply, title, unit, min_val, max_val):

        self.root = root

        self.target = target_entry

        self.on_apply = on_apply

        self.min_val = min_val

        self.max_val = max_val

        self.buffer = target_entry.get()

        BG = '#0d1117'

        KEY_BG = '#1e293b'

        KEY_FG = '#e2e8f0'

        ENTER_BG = '#22c55e'

        DEL_BG = '#ef4444'

        CANCEL_BG = '#64748b'

        # Overlay

        self.overlay = tk.Frame(root, bg=BG)

        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)

        self.overlay.bind('<Button-1>', lambda e: None)

        # Center card

        card = tk.Frame(self.overlay, bg='#111620', highlightbackground='#2a3244', highlightthickness=1)

        card.place(relx=0.5, rely=0.5, anchor='center')

        # Title

        tk.Label(card, text=title, font=('Segoe UI', 14, 'bold'),

                 bg='#111620', fg='#e2e8f0').pack(padx=30, pady=(20, 5))

        # Display

        display_frame = tk.Frame(card, bg='#0f1923', highlightbackground='#3b82f6', highlightthickness=2)

        display_frame.pack(padx=30, pady=10, fill=tk.X)

        self.display_var = tk.StringVar(value=self.buffer)

        self.display_label = tk.Label(

            display_frame, textvariable=self.display_var,

            font=('Consolas', 28, 'bold'), bg='#0f1923', fg='#00ff88',

            anchor='e', padx=15, pady=10

        )

        self.display_label.pack(fill=tk.X)

        if unit:

            tk.Label(card, text=unit, font=('Segoe UI', 10),

                     bg='#111620', fg='#64748b').pack()

        if min_val is not None and max_val is not None:

            tk.Label(card, text=f'Phạm vi: {min_val} – {max_val}',

                     font=('Segoe UI', 9), bg='#111620', fg='#64748b').pack(pady=(0, 5))

        # Numpad grid

        pad = tk.Frame(card, bg='#111620')

        pad.pack(padx=30, pady=5)

        buttons = [

            ['7', '8', '9'],

            ['4', '5', '6'],

            ['1', '2', '3'],

            ['C', '0', '⌫'],

        ]

        for row in buttons:

            rf = tk.Frame(pad, bg='#111620')

            rf.pack(pady=3)

            for key in row:

                if key == 'C':

                    bg, fg = CANCEL_BG, 'white'

                    cmd = self._clear

                elif key == '⌫':

                    bg, fg = DEL_BG, 'white'

                    cmd = self._backspace

                else:

                    bg, fg = KEY_BG, KEY_FG

                    cmd = lambda k=key: self._type(k)

                tk.Button(

                    rf, text=key, font=('Segoe UI Semibold', 16),

                    bg=bg, fg=fg, activebackground='#3b82f6', activeforeground='white',

                    relief=tk.FLAT, bd=0, width=4, height=1,

                    cursor='hand2', command=cmd

                ).pack(side=tk.LEFT, padx=3, ipady=8)

        # Bottom buttons: Cancel + Apply

        btn_frame = tk.Frame(card, bg='#111620')

        btn_frame.pack(padx=30, pady=(10, 20), fill=tk.X)

        tk.Button(

            btn_frame, text='✖ Hủy', font=('Segoe UI', 12, 'bold'),

            bg=CANCEL_BG, fg='white', activebackground='#475569',

            relief=tk.FLAT, bd=0, cursor='hand2',

            command=self.dismiss

        ).pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True, ipady=8)

        tk.Button(

            btn_frame, text='✔ Áp dụng', font=('Segoe UI', 12, 'bold'),

            bg=ENTER_BG, fg='white', activebackground='#16a34a',

            relief=tk.FLAT, bd=0, cursor='hand2',

            command=self._apply

        ).pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True, ipady=8)

        # Error label

        self.err_label = tk.Label(card, text='', font=('Segoe UI', 9),

                                  bg='#111620', fg='#ef4444')

        self.err_label.pack(pady=(0, 5))

        self.overlay.lift()

    def _type(self, digit):

        self.buffer += digit

        self.display_var.set(self.buffer)

    def _backspace(self):

        if self.buffer:

            self.buffer = self.buffer[:-1]

            self.display_var.set(self.buffer if self.buffer else '')

    def _clear(self):

        self.buffer = ''

        self.display_var.set('')

    def _apply(self):

        if not self.buffer:

            self.err_label.config(text='⚠ Vui lòng nhập giá trị')

            return

        try:

            val = int(self.buffer)

        except ValueError:

            self.err_label.config(text='⚠ Giá trị không hợp lệ')

            return

        if self.min_val is not None and val < self.min_val:

            self.err_label.config(text=f'⚠ Tối thiểu {self.min_val}')

            return

        if self.max_val is not None and val > self.max_val:

            self.err_label.config(text=f'⚠ Tối đa {self.max_val}')

            return

        self.target.delete(0, tk.END)

        self.target.insert(0, str(val))

        if self.on_apply:

            self.on_apply()

        self.dismiss()

    def dismiss(self):

        VirtualNumpad._instance = None

        try:

            self.overlay.destroy()

        except Exception:

            pass

class LoginWindow:

    """Clean centered login screen — dark theme desktop"""

    def __init__(self, root, on_success):

        self.root = root

        self.on_success = on_success

        # ── Colors ──

        BG       = '#0b0f19'

        CARD     = '#111827'

        BORDER   = '#1e293b'

        TXT_W    = '#ffffff'

        TXT1     = '#e2e8f0'

        TXT2     = '#94a3b8'

        TXT3     = '#64748b'

        BLUE     = '#3b82f6'

        BLUE_DK  = '#2563eb'

        CYAN     = '#06b6d4'

        RED      = '#ef4444'

        INPUT_BG = '#0f1629'

        # ── Full-screen overlay ──

        self.overlay = tk.Frame(root, bg=BG)

        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)

        self.overlay.lift()

        # ── Centered wrapper ──

        center = tk.Frame(self.overlay, bg=BG)

        center.place(relx=0.5, rely=0.5, anchor='center')

        # ── Logo icon ──

        logo_box = tk.Frame(center, bg=BLUE, highlightbackground=BLUE_DK, highlightthickness=2)

        logo_box.pack(pady=(0, 16))

        tk.Label(

            logo_box, text='☀', font=('Segoe UI', 26),

            bg=BLUE, fg=TXT_W, padx=14, pady=6

        ).pack()

        # ── Title ──

        tk.Label(

            center, text='Solar Clean',

            font=('Segoe UI', 28, 'bold'), bg=BG, fg=TXT_W

        ).pack()

        tk.Label(

            center, text='HỆ THỐNG VỆ SINH TẤM PIN MẶT TRỜI',

            font=('Segoe UI', 9), bg=BG, fg=CYAN, anchor='center'

        ).pack(pady=(2, 24))

        # ── Card ──

        card = tk.Frame(

            center, bg=CARD,

            highlightbackground=BORDER, highlightthickness=1

        )

        card.pack()

        self._card = card

        inner = tk.Frame(card, bg=CARD)

        inner.pack(padx=40, pady=32)

        # Title

        tk.Label(

            inner, text='Đăng nhập',

            font=('Segoe UI', 18, 'bold'), bg=CARD, fg=TXT_W, anchor='w'

        ).pack(anchor='w')

        tk.Label(

            inner, text='Nhập tài khoản để truy cập hệ thống',

            font=('Segoe UI', 10), bg=CARD, fg=TXT3, anchor='w'

        ).pack(anchor='w', pady=(3, 20))

        # ── Error banner (hidden) ──

        self.err_frame = tk.Frame(inner, bg='#1c1017',

                                  highlightbackground='#3b1520', highlightthickness=1)

        self.err_label = tk.Label(self.err_frame, text='', font=('Segoe UI', 10),

                                  bg='#1c1017', fg=RED, anchor='w', padx=12, pady=8)

        self.err_label.pack(fill=tk.X)

        # ── Username ──

        tk.Label(

            inner, text='Tài khoản', font=('Segoe UI', 10, 'bold'),

            bg=CARD, fg=TXT2, anchor='w'

        ).pack(fill=tk.X, pady=(0, 5))

        self.user_frame = tk.Frame(inner, bg=INPUT_BG,

            highlightbackground=BORDER, highlightthickness=1, highlightcolor=BLUE)

        self.user_frame.pack(fill=tk.X)

        uf = tk.Frame(self.user_frame, bg=INPUT_BG)

        uf.pack(fill=tk.X, padx=10, pady=1)

        tk.Label(uf, text='👤', font=('Segoe UI', 12), bg=INPUT_BG, fg=TXT3

                ).pack(side=tk.LEFT, padx=(0, 8))

        self.user_var = tk.StringVar()

        self.user_entry = tk.Entry(

            uf, textvariable=self.user_var,

            font=('Segoe UI', 12), bg=INPUT_BG, fg=TXT1,

            insertbackground=TXT1, relief=tk.FLAT, bd=0, width=28

        )

        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)

        # ── Password ──

        tk.Label(

            inner, text='Mật khẩu', font=('Segoe UI', 10, 'bold'),

            bg=CARD, fg=TXT2, anchor='w'

        ).pack(fill=tk.X, pady=(16, 5))

        self.pass_frame = tk.Frame(inner, bg=INPUT_BG,

            highlightbackground=BORDER, highlightthickness=1, highlightcolor=BLUE)

        self.pass_frame.pack(fill=tk.X)

        pf = tk.Frame(self.pass_frame, bg=INPUT_BG)

        pf.pack(fill=tk.X, padx=10, pady=1)

        tk.Label(pf, text='🔒', font=('Segoe UI', 12), bg=INPUT_BG, fg=TXT3

                ).pack(side=tk.LEFT, padx=(0, 8))

        self.pass_var = tk.StringVar()

        self.pass_entry = tk.Entry(

            pf, textvariable=self.pass_var, show='●',

            font=('Segoe UI', 12), bg=INPUT_BG, fg=TXT1,

            insertbackground=TXT1, relief=tk.FLAT, bd=0

        )

        self.pass_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)

        self._show_pass = False

        self.eye_btn = tk.Label(pf, text='👁', font=('Segoe UI', 12),

                                bg=INPUT_BG, fg=TXT3, cursor='hand2')

        self.eye_btn.pack(side=tk.RIGHT, padx=(8, 0))

        self.eye_btn.bind('<Button-1>', self._toggle_password)

        # ── Login button ──

        self.login_btn = tk.Button(

            inner, text='Đăng nhập', font=('Segoe UI', 13, 'bold'),

            bg=BLUE, fg='white', activebackground=BLUE_DK, activeforeground='white',

            relief=tk.FLAT, bd=0, cursor='hand2', command=self.do_login

        )

        self.login_btn.pack(fill=tk.X, ipady=10, pady=(22, 0))

        self.login_btn.bind('<Enter>', lambda e: self.login_btn.configure(bg=BLUE_DK))

        self.login_btn.bind('<Leave>', lambda e: self.login_btn.configure(bg=BLUE))

        # ── Version ──

        tk.Label(

            center, text=f'v{CONFIG["APP_VERSION"]}',

            font=('Segoe UI', 8), bg=BG, fg=TXT3

        ).pack(pady=(14, 0))

        # ── Bindings ──

        self.user_entry.bind('<Return>', lambda e: self.pass_entry.focus())

        self.pass_entry.bind('<Return>', lambda e: self.do_login())

        self.user_entry.bind('<Button-1>', lambda e: self.root.after(50, lambda: VirtualKeyboard.show(

            self.root, self.user_entry, is_password=False,

            on_confirm=self._open_pass_keyboard)))

        self.pass_entry.bind('<Button-1>', lambda e: self.root.after(50, lambda: VirtualKeyboard.show(

            self.root, self.pass_entry, is_password=True,

            on_confirm=self.do_login)))

        self.root.after(100, self.user_entry.focus_set)

        self.user_entry.bind('<FocusIn>', lambda e: self.user_frame.configure(highlightbackground=BLUE))

        self.user_entry.bind('<FocusOut>', lambda e: self.user_frame.configure(highlightbackground=BORDER))

        self.pass_entry.bind('<FocusIn>', lambda e: self.pass_frame.configure(highlightbackground=BLUE))

        self.pass_entry.bind('<FocusOut>', lambda e: self.pass_frame.configure(highlightbackground=BORDER))

    def _toggle_password(self, event=None):

        self._show_pass = not self._show_pass

        if self._show_pass:

            self.pass_entry.configure(show='')

            self.eye_btn.configure(text='🙈')

        else:

            self.pass_entry.configure(show='●')

            self.eye_btn.configure(text='👁')

    def _open_pass_keyboard(self):

        """Tự động mở bàn phím ảo cho mật khẩu sau khi nhập username xong"""

        self.pass_entry.focus_set()

        self.root.after(100, lambda: VirtualKeyboard.show(

            self.root, self.pass_entry, is_password=True,

            on_confirm=self.do_login))

    def _shake_card(self):

        """Shake animation không chặn main thread"""

        offsets = [8, -16, 12, -8, 4, 0]

        card = self._card

        def do_shake(i=0):

            if i >= len(offsets):

                card.pack_configure(padx=(40, 40))

                return

            dx = offsets[i]

            card.pack_configure(padx=(40 + dx, 40 - dx))

            self.root.after(30, lambda: do_shake(i + 1))

        do_shake()

    def do_login(self):

        u = self.user_var.get().strip()

        p = self.pass_var.get().strip()

        if not u or not p:

            self.err_label.config(text='⚠ Vui lòng nhập tài khoản và mật khẩu')

            self.err_frame.pack(fill=tk.X, pady=(0, 14))

            return

        # Check master admin

        if u == CONFIG['AUTH_USERNAME'] and p == CONFIG['AUTH_PASSWORD']:

            self.overlay.destroy()

            print('✅ Login successful (admin) — launching main application...')

            self.on_success()

            return

        # Check registered accounts

        accounts_file = _runtime_path('taikhoan', 'accounts.json')

        try:

            if os.path.exists(accounts_file):

                with open(accounts_file, 'r', encoding='utf-8') as f:

                    data = json.load(f)

                    accounts = data.get('accounts', [])

                salt = 'solarpanel2025'

                pw_hash = hashlib.sha256(f'{salt}:{p}'.encode()).hexdigest()

                for acc in accounts:

                    if acc.get('username', '').lower() == u.lower():

                        if acc.get('status') != 'approved':

                            self.err_label.config(text='⏳ Tài khoản đang chờ duyệt')

                            self.err_frame.pack(fill=tk.X, pady=(0, 14))

                            return

                        if acc.get('password_hash') == pw_hash:

                            self.overlay.destroy()

                            print(f'✅ Login successful ({u}) — launching main application...')

                            self.on_success()

                            return

        except Exception as e:

            print(f"Account check error: {e}")

        self.err_label.config(text='❌ Sai tài khoản hoặc mật khẩu')

        self.err_frame.pack(fill=tk.X, pady=(0, 14))

        self.pass_var.set('')

        self.pass_entry.focus_set()

        # Shake effect (non-blocking)

        self._shake_card()

class SolarPanelCleaningApp:

    """Ứng dụng chính với GUI và điều khiển PLC - TFLite version"""

    def __init__(self, root):

        self.root = root

        self.root.title(CONFIG['APP_TITLE'])

        self.root.state('zoomed')  # Maximized với title bar chuẩn Windows

        self.root.configure(bg='#2c3e50')

        # Components

        self.detector = None

        self.plc = None

        self.camera = None

        self.yolo_model = None  # Model YOLOv8 detect (leaf, bird_drop, crack)

        self.panel_seg_model = None  # Model YOLOv8-Seg (nhận diện chính xác tấm pin)

        self.is_running = False

        self.camera_preview_running = False  # Camera preview (chỉ hiển thị, không AI)

        self.camera_lock = threading.Lock()  # Lock để bảo vệ camera access

        self.scrollable_canvas = None  # Canvas cho scrollbar

        # Web server

        self.web_server_thread = None

        self.web_server_running = False

        # Stats

        self.total_frames = 0

        self.cleaning_count = 0

        self.start_time = time.time()

        # Detection tracking

        self.detection_start_time = None

        self.last_detected_class = None

        self.is_detection_confirmed = False

        # ✅ Kết quả AI để Web đọc (Web KHÔNG chạy AI riêng)

        self._last_p_dirty = 0.0

        self._last_area_ratio = 0.0

        self._last_label_name = 'Unknown'

        self._last_pred_probs = [0.0, 0.0]

        self._last_pred_class = 0

        self._last_frame = None

        self._last_cnn_patch_frame = None

        self._last_yolo_panel_frame = None

        self._last_confidence = 0.0

        self._last_dirty_patch_count = 0

        self._last_valid_patch_count = 0

        self._last_nopanel_patch_count = 0

        self._last_cnn_active = False

        self._last_panel_detected = False

        self._last_yolo_clean_faults = []

        self._last_yolo_crack_faults = []

        # ⚡ PZEM-017 Power Monitoring

        self.power_monitor = None

        self.efficiency_tracker = None

        self._last_power_data = {'voltage': 0, 'current': 0, 'power': 0, 'energy': 0}

        self._last_efficiency_data = None

        self._power_window = None  # PowerAnalysisWindow reference

        # Create UI

        self.create_ui()

        # Web module sẽ được gán khi start web server

        self.web_module = None

        # ☁️ Cloud API Client

        self.cloud_client = None

        self._cloud_push_thread = None

        # Initialize (gọi start_web_server bên trong → gán self.web_module)

        self.initialize_system()

        # Start command queue processor

        self.process_web_commands()

        # Load accounts on startup

        self.root.after(500, self.refresh_accounts)

    def process_web_commands(self):

        """Xử lý lệnh từ Web qua queue (thread-safe)"""

        try:

            if self.web_server_running and self.web_module:

                # Xử lý tất cả lệnh trong queue

                while not self.web_module.command_queue.empty():

                    cmd, value = self.web_module.command_queue.get_nowait()

                    print(f"📥 Received command from Web: {cmd} = {value}")

                    # Xử lý lệnh camera

                    if cmd == 'camera':

                        # Hot-swap camera với lock để tránh xung đột

                        with self.camera_lock:

                            # Tạo camera mới

                            new_camera = self._open_camera(value)

                            if new_camera:

                                # Release camera cũ

                                if self.camera:

                                    self.camera.release()

                                    time.sleep(0.1)  # Đợi một chút

                                # Gán camera mới

                                self.camera = new_camera

                                # Sync với Web

                                self.web_module.camera = self.camera

                                # Update UI

                                self.camera_id_var.set(str(value))

                                print(f"✅ Camera updated from Web: {value}")

                            else:

                                print(f"❌ Cannot open Camera {value} from Web")

                    # Xử lý lệnh threshold

                    elif cmd == 'threshold':

                        CONFIG['DIRT_AREA_THRESHOLD'] = float(value)

                        threshold_percent = int(value * 100)

                        self.dirt_threshold_var.set(str(threshold_percent))  # Update input

                        self.threshold_info_label.config(

                            text=f'Sẽ vệ sinh khi tỷ lệ patch bẩn ≥ {threshold_percent}%'

                        )

                        print(f"✅ Threshold updated from Web: {threshold_percent}%")

                    # Xử lý lệnh cnn_dirty_threshold

                    elif cmd == 'cnn_dirty_threshold':

                        CONFIG['CNN_DIRTY_THRESHOLD'] = float(value)

                        threshold_percent = int(value * 100)

                        self.cnn_threshold_var.set(str(threshold_percent))  # Update input

                        self.cnn_threshold_info_label.config(

                            text=f'CNN decision threshold: {threshold_percent}%'

                        )

                        print(f"✅ CNN threshold updated from Web: {threshold_percent}%")

                    # Xử lý lệnh snapshot_interval

                    elif cmd == 'snapshot_interval':

                        CONFIG['SNAPSHOT_INTERVAL'] = int(value)

                        interval_minutes = int(value) // 60

                        self.snapshot_interval_var.set(str(interval_minutes))  # Update input

                        self.interval_info_label.config(text=f'AI chạy mỗi {interval_minutes} phút')

                        print(f"✅ Snapshot interval updated from Web: {interval_minutes} phút ({value}s)")

                    # Xử lý lệnh vệ sinh thủ công từ Web

                    # Update PLC IP from Web/App without reconnecting

                    elif cmd == 'plc_ip_update':

                        new_ip = str(value).strip()

                        CONFIG['PLC']['IP'] = new_ip

                        self.plc_ip_var.set(new_ip)

                        self.plc_info_label.config(

                            text=f"IP: {CONFIG['PLC']['IP']} | DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0"

                        )

                        print(f"✅ PLC IP updated from Web: {new_ip}")

                    # Manual clean from Web/App

                    elif cmd == 'manual_clean':

                        print("🧹 Manual cleaning triggered from Web")

                        if self.plc and self.plc.is_connected:

                            success = self.plc.trigger_cleaning()

                            if success:

                                self.cleaning_count += 1

                                self.cleaning_label.config(text=f'Cleaned: {self.cleaning_count}')

                                if self.efficiency_tracker:

                                    self.efficiency_tracker.on_cleaning_started(

                                        trigger_reason='Manual Clean (Web)',

                                        dirty_ratio=0.0,

                                        ai_label='Manual',

                                        ai_confidence=1.0,

                                    )

                                print("✅ Manual cleaning activated successfully")

                            else:

                                print("⚠️ Manual cleaning failed (cooldown or error)")

                        else:

                            print("❌ PLC not connected - cannot trigger manual cleaning")

                    # Xử lý lệnh BẮT ĐẦU hệ thống từ Web

                    elif cmd == 'system_start':

                        print("â–️ System START command from Web")

                        if not self.is_running:

                            # Gọi start_monitoring() trong main thread

                            self.root.after(0, self.start_monitoring)

                            print("✅ Starting monitoring from Web command")

                        else:

                            print("⚠️ System already running")

                    # Xử lý lệnh DỪNG hệ thống từ Web

                    elif cmd == 'system_stop':

                        print("⏹️ System STOP command from Web")

                        if self.is_running:

                            # Gọi stop_monitoring() trong main thread

                            self.root.after(0, self.stop_monitoring)

                            print("✅ Stopping monitoring from Web command")

                        else:

                            print("⚠️ System already stopped")

                    # Xử lý lệnh kết nối lại PLC từ Web

                    elif cmd == 'plc_reconnect':

                        new_ip = str(value) if value else CONFIG['PLC'].get('IP', '192.168.1.1')

                        print(f"🔌 PLC reconnect command from Web: {new_ip}")

                        CONFIG['PLC']['IP'] = new_ip

                        self.plc_ip_var.set(new_ip)

                        if self.plc:

                            try:

                                self.plc.disconnect()

                            except Exception:

                                pass

                            try:

                                self.plc.config['IP'] = new_ip

                                self.plc.connect()

                                if self.plc.is_connected:

                                    self.plc_status_label.config(text='CONNECTED', fg='#22c55e')

                                    self.plc_info_label.config(

                                        text=f"IP: {CONFIG['PLC']['IP']} | DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0"

                                    )

                                    print(f"✅ PLC reconnected to {new_ip}")

                                else:

                                    self.plc_status_label.config(text='CONNECTION FAILED', fg='#ef4444')

                                    print(f"❌ PLC reconnect failed: {new_ip}")

                            except Exception as e:

                                print(f"❌ PLC reconnect error: {e}")

                    # Xử lý thông báo đăng ký mới từ Web/App

                    elif cmd == 'new_registration':

                        username = value.get('username', '???') if isinstance(value, dict) else str(value)

                        fullname = value.get('fullname', '') if isinstance(value, dict) else ''

                        print(f"📝 New registration notification: {username}")

                        # Auto-refresh account list

                        self.root.after(0, self.refresh_accounts)

                        # Show notification

                        self.root.after(100, lambda u=username, fn=fullname: messagebox.showinfo(

                            "Đăng ký mới",

                            f"📝 Có tài khoản mới đăng ký!\n\n"

                            f"Tên: {u}\n"

                            f"{'Họ tên: ' + fn + chr(10) if fn else ''}"

                            f"Trạng thái: Chờ duyệt\n\n"

                            f"Vào mục Quản lý Tài khoản để duyệt."

                        ))

        except Exception as e:

            print(f"Command queue error: {e}")

            import traceback

            traceback.print_exc()

        # Schedule lại sau 100ms

        self.root.after(100, self.process_web_commands)

    def create_ui(self):

        """Tạo giao diện - Professional Industrial SCADA Style"""

        # ===== TTK THEME SETUP =====

        style = ttk.Style()

        style.theme_use('clam')

        # Color palette

        C_BG = '#0f1923'       # Dark background

        C_PANEL = '#172030'    # Panel background

        C_CARD = '#1e293b'     # Card background

        C_BORDER = '#334155'   # Border

        C_HEADER = '#111827'   # Header bar

        C_TEXT1 = '#e2e8f0'    # Primary text

        C_TEXT2 = '#94a3b8'    # Secondary text

        C_TEXT3 = '#64748b'    # Muted text

        C_GREEN = '#22c55e'    # OK / Success

        C_RED = '#ef4444'      # Error / Danger

        C_BLUE = '#3b82f6'     # Info / Accent

        C_YELLOW = '#eab308'   # Warning

        C_ORANGE = '#f59e0b'   # University color

        C_CYAN = '#06b6d4'     # Metrics

        self.root.configure(bg=C_BG)

        self._colors = {

            'bg': C_BG, 'panel': C_PANEL, 'card': C_CARD, 'border': C_BORDER,

            'header': C_HEADER, 'text1': C_TEXT1, 'text2': C_TEXT2, 'text3': C_TEXT3,

            'green': C_GREEN, 'red': C_RED, 'blue': C_BLUE, 'yellow': C_YELLOW,

            'orange': C_ORANGE, 'cyan': C_CYAN

        }

        # TTK Styles

        style.configure('Card.TFrame', background=C_CARD)

        style.configure('Panel.TFrame', background=C_PANEL)

        style.configure('Header.TFrame', background=C_HEADER)

        style.configure('Green.Horizontal.TProgressbar', troughcolor=C_BG, background=C_GREEN, thickness=8)

        style.configure('Red.Horizontal.TProgressbar', troughcolor=C_BG, background=C_RED, thickness=8)

        style.configure('Blue.Horizontal.TProgressbar', troughcolor=C_BG, background=C_BLUE, thickness=8)

        style.configure('Cyan.Horizontal.TProgressbar', troughcolor=C_BG, background=C_CYAN, thickness=8)

        # ===== HEADER BAR (compact) =====

        header_frame = tk.Frame(self.root, bg=C_HEADER, height=64)

        header_frame.pack(fill=tk.X)

        header_frame.pack_propagate(False)

        header_content = tk.Frame(header_frame, bg=C_HEADER)

        header_content.place(relx=0.5, rely=0.5, anchor='center')

        # Logo

        try:

            logo_path = _res('ctut.webp')

            if os.path.exists(logo_path):

                logo_img = Image.open(logo_path)

                logo_img = logo_img.resize((44, 44), Image.Resampling.LANCZOS)

                logo_photo = ImageTk.PhotoImage(logo_img)

                logo_label = tk.Label(header_content, image=logo_photo, bg=C_HEADER)

                logo_label.image = logo_photo

                logo_label.pack(side=tk.LEFT, padx=(0, 12))

        except Exception as e:

            print(f"Logo load error: {e}")

        text_container = tk.Frame(header_content, bg=C_HEADER)

        text_container.pack(side=tk.LEFT)

        tk.Label(

            text_container,

            text="TRƯỜNG ĐẠI HỌC KỸ THUẬT - CÔNG NGHỆ CẦN THƠ",

            font=('Segoe UI', 11, 'bold'),

            bg=C_HEADER, fg=C_ORANGE

        ).pack(anchor='w')

        # Title + version on same line

        title_row = tk.Frame(text_container, bg=C_HEADER)

        title_row.pack(anchor='w')

        tk.Label(

            title_row,

            text=CONFIG['APP_TITLE'],

            font=('Segoe UI', 13, 'bold'),

            bg=C_HEADER, fg=C_TEXT1

        ).pack(side=tk.LEFT)

        tk.Label(

            title_row,

            text=f"  v{CONFIG['APP_VERSION']}",

            font=('Segoe UI', 9),

            bg=C_HEADER, fg=C_TEXT3

        ).pack(side=tk.LEFT, padx=(6, 0))

        # ⚡ Power Analysis button (right side of header)

        power_btn = tk.Button(

            header_frame, text='⚡ Power', command=self.open_power_window,

            font=('Segoe UI', 10, 'bold'), bg='#f59e0b', fg='#000',

            cursor='hand2', relief=tk.FLAT, bd=0, padx=14, pady=4,

            activebackground='#d97706', activeforeground='#000'

        )

        power_btn.place(relx=1.0, rely=0.5, anchor='e', x=-16)

        # ===== MAIN CONTENT =====

        main_frame = tk.Frame(self.root, bg=C_BG)

        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Left panel - Video

        left_container = tk.Frame(main_frame, bg=C_PANEL, relief=tk.FLAT, bd=0,

                                  highlightbackground=C_BORDER, highlightthickness=1)

        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))

        main_frame.columnconfigure(0, weight=65)

        main_frame.columnconfigure(1, weight=35)

        left_frame = tk.Frame(left_container, bg=C_PANEL)

        left_frame.pack(fill=tk.BOTH, expand=True)

        # Camera section header

        cam_header = tk.Frame(left_frame, bg=C_HEADER, height=32)

        cam_header.pack(fill=tk.X)

        cam_header.pack_propagate(False)

        tk.Label(cam_header, text='  LIVE CAMERA', font=('Segoe UI', 10, 'bold'),

                 bg=C_HEADER, fg=C_TEXT2).pack(side=tk.LEFT, padx=8, pady=4)

        # Camera control (inline in header)

        cam_control = tk.Frame(cam_header, bg=C_HEADER)

        cam_control.pack(side=tk.RIGHT, padx=6)

        tk.Label(cam_control, text='CAM:', bg=C_HEADER, fg=C_TEXT3,

                 font=('Segoe UI', 8, 'bold')).pack(side=tk.LEFT, padx=(0,3))

        self.camera_id_var = tk.StringVar(value=str(CONFIG['CAMERA_ID']))

        camera_spin = tk.Spinbox(cam_control, from_=0, to=5, width=3,

                                 textvariable=self.camera_id_var, font=('Segoe UI', 9),

                                 bg=C_BG, fg=C_TEXT1, buttonbackground=C_CARD,

                                 insertbackground=C_TEXT1, relief=tk.FLAT, bd=1)

        camera_spin.pack(side=tk.LEFT, padx=2)

        switch_cam_btn = tk.Button(

            cam_control, text='Switch', command=self.switch_camera,

            font=('Segoe UI', 8, 'bold'), bg=C_BLUE, fg='white',

            cursor='hand2', relief=tk.FLAT, bd=0, padx=8, pady=1,

            activebackground='#2563eb', activeforeground='white'

        )

        switch_cam_btn.pack(side=tk.LEFT, padx=3)

        # Video display

        video_frame = tk.Frame(left_frame, bg='#000000', height=400)

        video_frame.pack(padx=4, pady=(4, 4), fill=tk.BOTH, expand=False)

        video_frame.pack_propagate(False)

        self.video_canvas = tk.Label(video_frame, bg='#000000',

                                     text='Đang khởi tạo camera...',

                                     font=('Segoe UI', 12),

                                     fg=C_TEXT3)

        self.video_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # Snapshot preview panel

        snap_header = tk.Frame(left_frame, bg=C_HEADER, height=30)

        snap_header.pack(fill=tk.X, padx=4)

        snap_header.pack_propagate(False)

        tk.Label(snap_header, text='  AI SNAPSHOT', font=('Segoe UI', 10, 'bold'),

                 bg=C_HEADER, fg=C_TEXT2).pack(side=tk.LEFT, padx=8, pady=3)

        snapshot_preview_frame = tk.Frame(left_frame, bg=C_CARD,

                                         highlightbackground=C_BORDER, highlightthickness=1)

        snapshot_preview_frame.pack(padx=4, pady=(0, 4), fill=tk.BOTH, expand=False)

        # Container cho snapshot

        snapshot_container = tk.Frame(snapshot_preview_frame, bg='#0a0e14', height=400)

        snapshot_container.pack(padx=2, pady=2, fill=tk.BOTH, expand=False)

        snapshot_container.pack_propagate(False)

        self.snapshot_canvas = tk.Label(

            snapshot_container, bg='#0a0e14',

            text='Waiting for first snapshot...',

            font=('Segoe UI', 10), fg=C_TEXT3

        )

        self.snapshot_canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.snapshot_info_label = tk.Label(

            snapshot_preview_frame,

            text='Pending first AI scan...',

            font=('Segoe UI', 8), bg=C_CARD, fg=C_TEXT3

        )

        self.snapshot_info_label.pack(pady=(2, 4))

        # ===== RIGHT PANEL =====

        right_container = tk.Frame(main_frame, bg=C_PANEL, width=380,

                                   highlightbackground=C_BORDER, highlightthickness=1)

        right_container.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(4, 0))

        right_container.pack_propagate(False)

        # Canvas and Scrollbar

        self.scrollable_canvas = tk.Canvas(right_container, bg=C_PANEL,

                                           highlightthickness=0, bd=0)

        scrollbar = ttk.Scrollbar(right_container, orient="vertical",

                                  command=self.scrollable_canvas.yview)

        right_frame = tk.Frame(self.scrollable_canvas, bg=C_PANEL)

        right_frame.bind(

            "<Configure>",

            lambda e: self.scrollable_canvas.configure(scrollregion=self.scrollable_canvas.bbox("all"))

        )

        self.scrollable_canvas.create_window((0, 0), window=right_frame, anchor="nw")

        self.scrollable_canvas.configure(yscrollcommand=scrollbar.set)

        self.scrollable_canvas.pack(side="left", fill="both", expand=True)

        scrollbar.pack(side="right", fill="y")

        # Mouse wheel

        def _on_right_mousewheel(event):

            self.scrollable_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        self.scrollable_canvas.bind("<Enter>", lambda e: self.scrollable_canvas.bind_all("<MouseWheel>", _on_right_mousewheel))

        self.scrollable_canvas.bind("<Leave>", lambda e: self.scrollable_canvas.unbind_all("<MouseWheel>"))

        # Touch/drag scroll — vuốt kéo chuẩn HMI touchscreen

        self._drag_y = None

        self._drag_started = False

        _DRAG_DEADZONE = 5  # pixels — phân biệt click vs drag

        def _on_drag_start(event):

            self._drag_y = event.y_root

            self._drag_started = False

        def _on_drag_motion(event):

            if self._drag_y is not None:

                dy = self._drag_y - event.y_root

                if not self._drag_started and abs(dy) < _DRAG_DEADZONE:

                    return  # Chưa đủ ngưỡng → bỏ qua (cho phép click bình thường)

                self._drag_started = True

                self.scrollable_canvas.yview_scroll(int(dy / 3), "units")

                self._drag_y = event.y_root

        def _on_drag_end(event):

            self._drag_y = None

            self._drag_started = False

        # Bind đệ quy cho mọi widget con (trừ Entry/Button/Spinbox)

        _no_drag_types = (tk.Entry, tk.Button, tk.Spinbox, ttk.Entry, ttk.Button)

        def _bind_drag_recursive(widget):

            if isinstance(widget, _no_drag_types):

                return  # Không bind drag lên input/button

            try:

                widget.bind("<ButtonPress-1>", _on_drag_start, add='+')

                widget.bind("<B1-Motion>", _on_drag_motion, add='+')

                widget.bind("<ButtonRelease-1>", _on_drag_end, add='+')

            except Exception:

                pass

            for child in widget.winfo_children():

                _bind_drag_recursive(child)

        self.scrollable_canvas.bind("<ButtonPress-1>", _on_drag_start)

        self.scrollable_canvas.bind("<B1-Motion>", _on_drag_motion)

        self.scrollable_canvas.bind("<ButtonRelease-1>", _on_drag_end)

        # Sau khi tất cả widget đã tạo xong, bind drag (gọi sau build_gui)

        self._bind_drag_to_panel = lambda: _bind_drag_recursive(right_frame)

        # Section header helper

        def section_header(parent, text):

            h = tk.Frame(parent, bg=C_HEADER, height=28)

            h.pack(fill=tk.X, padx=8, pady=(8, 0))

            h.pack_propagate(False)

            tk.Label(h, text=f'  {text}', font=('Segoe UI', 9, 'bold'),

                     bg=C_HEADER, fg=C_TEXT3).pack(side=tk.LEFT, padx=6, pady=2)

            return h

        # PLC Status

        section_header(right_frame, 'PLC CONNECTION')

        plc_frame = tk.Frame(right_frame, bg=C_CARD,

                             highlightbackground=C_BORDER, highlightthickness=1)

        plc_frame.pack(pady=(2, 0), padx=8, fill=tk.X)

        plc_config_frame = tk.Frame(plc_frame, bg=C_CARD)

        plc_config_frame.pack(pady=6, padx=8, fill=tk.X)

        tk.Label(plc_config_frame, text='IP:', font=('Segoe UI', 9, 'bold'),

                 bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=(0, 4))

        self.plc_ip_var = tk.StringVar(value=CONFIG['PLC']['IP'])

        self.plc_ip_entry = tk.Entry(

            plc_config_frame, textvariable=self.plc_ip_var,

            font=('Consolas', 10), width=14,

            bg=C_BG, fg=C_TEXT1, insertbackground=C_TEXT1,

            relief=tk.FLAT, bd=1, highlightbackground=C_BORDER, highlightthickness=1

        )

        self.plc_ip_entry.pack(side=tk.LEFT, padx=4)

        self.plc_connect_btn = tk.Button(

            plc_config_frame, text='Connect', command=self.reconnect_plc,

            font=('Segoe UI', 8, 'bold'), bg=C_BLUE, fg='white',

            cursor='hand2', padx=10, relief=tk.FLAT, bd=0,

            activebackground='#2563eb', activeforeground='white'

        )

        self.plc_connect_btn.pack(side=tk.LEFT, padx=4)

        self.plc_status_label = tk.Label(

            plc_frame, text='NOT CONNECTED',

            font=('Segoe UI', 10, 'bold'), bg=C_CARD, fg=C_RED

        )

        self.plc_status_label.pack(pady=2)

        self.plc_info_label = tk.Label(

            plc_frame,

            text=f"Target: DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0",

            font=('Consolas', 8), bg=C_CARD, fg=C_TEXT3

        )

        self.plc_info_label.pack(pady=(0, 6))

        # Dirt Area Threshold

        section_header(right_frame, 'CLEANING CONFIG')

        threshold_frame = tk.Frame(right_frame, bg=C_CARD,

                                   highlightbackground=C_BORDER, highlightthickness=1)

        threshold_frame.pack(pady=(2, 0), padx=8, fill=tk.X)

        threshold_config_frame = tk.Frame(threshold_frame, bg=C_CARD)

        threshold_config_frame.pack(pady=6, padx=8, fill=tk.X)

        tk.Label(threshold_config_frame, text='Dirty patch threshold:',

                 font=('Segoe UI', 9), bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=(0, 4))

        # HMI-style numeric input with ▼ ▲ buttons

        thr_spin_frame = tk.Frame(threshold_config_frame, bg=C_BORDER)

        thr_spin_frame.pack(side=tk.LEFT, padx=2)

        self._thr_down_btn = tk.Button(

            thr_spin_frame, text='\u25BC', font=('Segoe UI', 9, 'bold'),

            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,

            activebackground=C_BLUE, activeforeground='white', cursor='hand2'

        )

        self._thr_down_btn.pack(side=tk.LEFT, padx=(1, 0), pady=1)

        self.dirt_threshold_var = tk.StringVar(value=str(int(CONFIG['DIRT_AREA_THRESHOLD'] * 100)))

        self.dirt_threshold_entry = tk.Entry(

            thr_spin_frame, textvariable=self.dirt_threshold_var,

            font=('Consolas', 12, 'bold'), width=4,

            bg=C_BG, fg='#00ff88', insertbackground=C_TEXT1,

            justify='center', relief=tk.FLAT, bd=0,

            highlightbackground=C_BORDER, highlightthickness=1

        )

        self.dirt_threshold_entry.pack(side=tk.LEFT, padx=1, pady=1, ipady=2)

        # Touch HMI: nhấn (click/tap) vào entry → hiện numpad

        self.dirt_threshold_entry.bind('<Button-1>', lambda e: self.root.after(50, lambda: VirtualNumpad.show(

            self.root, self.dirt_threshold_entry,

            on_apply=self.apply_threshold,

            title='Ngưỡng patch bẩn', unit='%', min_val=0, max_val=100

        )))

        self._thr_up_btn = tk.Button(

            thr_spin_frame, text='\u25B2', font=('Segoe UI', 9, 'bold'),

            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,

            activebackground=C_BLUE, activeforeground='white', cursor='hand2'

        )

        self._thr_up_btn.pack(side=tk.LEFT, padx=(0, 1), pady=1)

        # Bind up/down with auto-repeat on hold

        self._setup_spin_button(self._thr_down_btn, self.dirt_threshold_var, -1, 0, 100)

        self._setup_spin_button(self._thr_up_btn, self.dirt_threshold_var, +1, 0, 100)

        tk.Label(threshold_config_frame, text='%', font=('Segoe UI', 10, 'bold'),

                 bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=2)

        self.threshold_apply_btn = tk.Button(

            threshold_config_frame, text='Apply', command=self.apply_threshold,

            font=('Segoe UI', 8, 'bold'), bg=C_GREEN, fg='white',

            cursor='hand2', padx=10, relief=tk.FLAT, bd=0,

            activebackground='#16a34a', activeforeground='white'

        )

        self.threshold_apply_btn.pack(side=tk.LEFT, padx=4)

        self.threshold_info_label = tk.Label(

            threshold_frame,

            text=f'Clean when dirty patch ratio >= {CONFIG["DIRT_AREA_THRESHOLD"]*100:.0f}%',

            font=('Segoe UI', 8), bg=C_CARD, fg=C_TEXT3

        )

        self.threshold_info_label.pack(pady=(0, 6))

        # CNN Classification Decision Threshold
        cnn_threshold_config_frame = tk.Frame(threshold_frame, bg=C_CARD)
        cnn_threshold_config_frame.pack(pady=4, padx=8, fill=tk.X)

        tk.Label(cnn_threshold_config_frame, text='CNN Class Threshold:',
                 font=('Segoe UI', 9), bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=(0, 4))

        cnn_thr_spin_frame = tk.Frame(cnn_threshold_config_frame, bg=C_BORDER)
        cnn_thr_spin_frame.pack(side=tk.LEFT, padx=2)

        self._cnn_thr_down_btn = tk.Button(
            cnn_thr_spin_frame, text='\u25BC', font=('Segoe UI', 9, 'bold'),
            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,
            activebackground=C_BLUE, activeforeground='white', cursor='hand2'
        )
        self._cnn_thr_down_btn.pack(side=tk.LEFT, padx=(1, 0), pady=1)

        self.cnn_threshold_var = tk.StringVar(value=str(int(CONFIG.get('CNN_DIRTY_THRESHOLD', 0.65) * 100)))
        self.cnn_threshold_entry = tk.Entry(
            cnn_thr_spin_frame, textvariable=self.cnn_threshold_var,
            font=('Consolas', 12, 'bold'), width=4,
            bg=C_BG, fg='#00ff88', insertbackground=C_TEXT1,
            justify='center', relief=tk.FLAT, bd=0,
            highlightbackground=C_BORDER, highlightthickness=1
        )
        self.cnn_threshold_entry.pack(side=tk.LEFT, padx=1, pady=1, ipady=2)

        # Touch HMI: click -> numpad
        self.cnn_threshold_entry.bind('<Button-1>', lambda e: self.root.after(50, lambda: VirtualNumpad.show(
            self.root, self.cnn_threshold_entry,
            on_apply=self.apply_cnn_threshold,
            title='Ngưỡng bẩn CNN', unit='%', min_val=0, max_val=100
        )))

        self._cnn_thr_up_btn = tk.Button(
            cnn_thr_spin_frame, text='\u25B2', font=('Segoe UI', 9, 'bold'),
            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,
            activebackground=C_BLUE, activeforeground='white', cursor='hand2'
        )
        self._cnn_thr_up_btn.pack(side=tk.LEFT, padx=(0, 1), pady=1)

        self._setup_spin_button(self._cnn_thr_down_btn, self.cnn_threshold_var, -1, 0, 100)
        self._setup_spin_button(self._cnn_thr_up_btn, self.cnn_threshold_var, +1, 0, 100)

        tk.Label(cnn_threshold_config_frame, text='%', font=('Segoe UI', 10, 'bold'),
                 bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=2)

        self.cnn_threshold_apply_btn = tk.Button(
            cnn_threshold_config_frame, text='Apply', command=self.apply_cnn_threshold,
            font=('Segoe UI', 8, 'bold'), bg=C_GREEN, fg='white',
            cursor='hand2', padx=10, relief=tk.FLAT, bd=0,
            activebackground='#16a34a', activeforeground='white'
        )
        self.cnn_threshold_apply_btn.pack(side=tk.LEFT, padx=4)

        self.cnn_threshold_info_label = tk.Label(
            threshold_frame,
            text=f'CNN decision threshold: {CONFIG.get("CNN_DIRTY_THRESHOLD", 0.65)*100:.0f}%',
            font=('Segoe UI', 8), bg=C_CARD, fg=C_TEXT3
        )
        self.cnn_threshold_info_label.pack(pady=(0, 6))

        # Snapshot Interval

        section_header(right_frame, 'SNAPSHOT SCHEDULE')

        snapshot_interval_frame = tk.Frame(right_frame, bg=C_CARD,

                                           highlightbackground=C_BORDER, highlightthickness=1)

        snapshot_interval_frame.pack(pady=(2, 0), padx=8, fill=tk.X)

        interval_config_frame = tk.Frame(snapshot_interval_frame, bg=C_CARD)

        interval_config_frame.pack(pady=6, padx=8, fill=tk.X)

        tk.Label(interval_config_frame, text='Interval:',

                 font=('Segoe UI', 9), bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=(0, 4))

        # HMI-style numeric input with ▼ ▲ buttons

        int_spin_frame = tk.Frame(interval_config_frame, bg=C_BORDER)

        int_spin_frame.pack(side=tk.LEFT, padx=2)

        self._int_down_btn = tk.Button(

            int_spin_frame, text='\u25BC', font=('Segoe UI', 9, 'bold'),

            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,

            activebackground=C_BLUE, activeforeground='white', cursor='hand2'

        )

        self._int_down_btn.pack(side=tk.LEFT, padx=(1, 0), pady=1)

        self.snapshot_interval_var = tk.StringVar(value=str(int(CONFIG['SNAPSHOT_INTERVAL'] / 60)))

        self.snapshot_interval_entry = tk.Entry(

            int_spin_frame, textvariable=self.snapshot_interval_var,

            font=('Consolas', 12, 'bold'), width=4,

            bg=C_BG, fg='#00ff88', insertbackground=C_TEXT1,

            justify='center', relief=tk.FLAT, bd=0,

            highlightbackground=C_BORDER, highlightthickness=1

        )

        self.snapshot_interval_entry.pack(side=tk.LEFT, padx=1, pady=1, ipady=2)

        # Touch HMI: nhấn (click/tap) vào entry → hiện numpad

        self.snapshot_interval_entry.bind('<Button-1>', lambda e: self.root.after(50, lambda: VirtualNumpad.show(

            self.root, self.snapshot_interval_entry,

            on_apply=self.apply_snapshot_interval,

            title='Chu kỳ AI phân tích', unit='phút', min_val=1, max_val=1440

        )))

        self._int_up_btn = tk.Button(

            int_spin_frame, text='\u25B2', font=('Segoe UI', 9, 'bold'),

            bg='#334155', fg=C_TEXT1, width=2, relief=tk.FLAT, bd=0,

            activebackground=C_BLUE, activeforeground='white', cursor='hand2'

        )

        self._int_up_btn.pack(side=tk.LEFT, padx=(0, 1), pady=1)

        # Bind up/down with auto-repeat on hold

        self._setup_spin_button(self._int_down_btn, self.snapshot_interval_var, -1, 1, 1440)

        self._setup_spin_button(self._int_up_btn, self.snapshot_interval_var, +1, 1, 1440)

        tk.Label(interval_config_frame, text='min', font=('Segoe UI', 10, 'bold'),

                 bg=C_CARD, fg=C_TEXT2).pack(side=tk.LEFT, padx=2)

        self.interval_apply_btn = tk.Button(

            interval_config_frame, text='Apply', command=self.apply_snapshot_interval,

            font=('Segoe UI', 8, 'bold'), bg=C_BLUE, fg='white',

            cursor='hand2', padx=10, relief=tk.FLAT, bd=0,

            activebackground='#2563eb', activeforeground='white'

        )

        self.interval_apply_btn.pack(side=tk.LEFT, padx=4)

        self.interval_info_label = tk.Label(

            snapshot_interval_frame,

            text=f'AI runs every {CONFIG["SNAPSHOT_INTERVAL"]//60} min',

            font=('Segoe UI', 8), bg=C_CARD, fg=C_TEXT3

        )

        self.interval_info_label.pack(pady=(0, 6))

        # Detection Status Banner

        section_header(right_frame, 'SYSTEM STATUS')

        self.status_frame = tk.Frame(right_frame, bg=C_GREEN,

                                     highlightbackground=C_GREEN, highlightthickness=2)

        self.status_frame.pack(pady=(2, 0), padx=8, fill=tk.X)

        self.status_label = tk.Label(

            self.status_frame, text='READY',

            font=('Segoe UI', 18, 'bold'), bg=C_GREEN, fg='white'

        )

        self.status_label.pack(pady=8)

        self.class_label = tk.Label(

            self.status_frame, text='Waiting...',

            font=('Segoe UI', 10), bg=C_GREEN,

            fg='white'

        )

        self.class_label.pack(pady=(0, 8))

        # Countdown label

        self.countdown_label = tk.Label(

            self.status_frame, text='',

            font=('Segoe UI', 11, 'bold'), bg=C_GREEN, fg='white'

        )

        self.countdown_label.pack(pady=(0, 8))

        # Metrics

        section_header(right_frame, 'AI METRICS')

        metrics_frame = tk.Frame(right_frame, bg=C_PANEL)

        metrics_frame.pack(pady=(2, 0), padx=8, fill=tk.BOTH, expand=True)

        self.create_metric(metrics_frame, "Dirty Patch Ratio", "dirt_prob", 0)

        # Class Probabilities

        class_frame = tk.Frame(metrics_frame, bg=C_CARD,

                               highlightbackground=C_BORDER, highlightthickness=1)

        class_frame.grid(row=1, column=0, pady=4, padx=0, sticky='ew')

        # Class header inside card

        tk.Label(class_frame, text='  AI CLASSIFICATION  (CNN — 2 Class)',

                 font=('Segoe UI', 9, 'bold'), bg=C_HEADER, fg=C_TEXT3,

                 anchor='w').pack(fill=tk.X, ipady=4)

        class_inner = tk.Frame(class_frame, bg=C_CARD)

        class_inner.pack(padx=8, pady=6, fill=tk.X)

        self.class_bars = {}

        class_labels = ['ban', 'sach']

        for i, label in enumerate(class_labels):

            self.create_class_bar(class_inner, label, i)

        # System Stats

        stats_info_frame = tk.Frame(metrics_frame, bg=C_CARD,

                                    highlightbackground=C_BORDER, highlightthickness=1)

        stats_info_frame.grid(row=2, column=0, pady=4, padx=0, sticky='ew')

        tk.Label(stats_info_frame, text='  STATISTICS',

                 font=('Segoe UI', 9, 'bold'), bg=C_HEADER, fg=C_TEXT3,

                 anchor='w').pack(fill=tk.X, ipady=4)

        stats_inner = tk.Frame(stats_info_frame, bg=C_CARD)

        stats_inner.pack(padx=8, pady=6, fill=tk.X)

        self.fps_label = tk.Label(stats_inner, text='FPS: 0.0',

                                 font=('Consolas', 10), bg=C_CARD, fg=C_CYAN)

        self.fps_label.pack(anchor='w', pady=2)

        self.frames_label = tk.Label(stats_inner, text='Frames: 0',

                                     font=('Consolas', 10), bg=C_CARD, fg=C_TEXT2)

        self.frames_label.pack(anchor='w', pady=2)

        self.cleaning_label = tk.Label(stats_inner, text='Cleaned: 0',

                                       font=('Segoe UI', 10, 'bold'), bg=C_CARD, fg=C_BLUE)

        self.cleaning_label.pack(anchor='w', pady=2)

        # ===== QUẢN LÝ TÀI KHOẢN =====

        section_header(right_frame, 'QUẢN LÝ TÀI KHOẢN')

        acc_frame = tk.Frame(right_frame, bg=C_CARD,

                             highlightbackground=C_BORDER, highlightthickness=1)

        acc_frame.pack(pady=(2, 0), padx=8, fill=tk.X)

        # Pending count badge

        acc_header_row = tk.Frame(acc_frame, bg=C_CARD)

        acc_header_row.pack(padx=8, pady=(6, 2), fill=tk.X)

        self.pending_count_label = tk.Label(

            acc_header_row, text='Chờ duyệt: 0',

            font=('Segoe UI', 10, 'bold'), bg=C_CARD, fg=C_YELLOW

        )

        self.pending_count_label.pack(side=tk.LEFT)

        self.approved_count_label = tk.Label(

            acc_header_row, text='Đã duyệt: 0',

            font=('Segoe UI', 10), bg=C_CARD, fg=C_GREEN

        )

        self.approved_count_label.pack(side=tk.LEFT, padx=(12, 0))

        # Account list area (Listbox)

        acc_list_frame = tk.Frame(acc_frame, bg=C_BG)

        acc_list_frame.pack(padx=8, pady=4, fill=tk.X)

        self.account_listbox = tk.Listbox(

            acc_list_frame, height=5,

            font=('Consolas', 9), bg=C_BG, fg=C_TEXT1,

            selectbackground=C_BLUE, selectforeground='white',

            activestyle='none', relief=tk.FLAT, bd=0,

            highlightbackground=C_BORDER, highlightthickness=1

        )

        self.account_listbox.pack(fill=tk.X, expand=True)

        # Account action buttons

        acc_btn_frame = tk.Frame(acc_frame, bg=C_CARD)

        acc_btn_frame.pack(padx=8, pady=(2, 6), fill=tk.X)

        self.acc_refresh_btn = tk.Button(

            acc_btn_frame, text='Tải lại',

            command=self.refresh_accounts,

            font=('Segoe UI', 8, 'bold'), bg=C_BLUE, fg='white',

            cursor='hand2', padx=8, relief=tk.FLAT, bd=0,

            activebackground='#2563eb', activeforeground='white'

        )

        self.acc_refresh_btn.pack(side=tk.LEFT, padx=2)

        self.acc_approve_btn = tk.Button(

            acc_btn_frame, text='✔ Duyệt',

            command=self.approve_selected_account,

            font=('Segoe UI', 8, 'bold'), bg=C_GREEN, fg='white',

            cursor='hand2', padx=8, relief=tk.FLAT, bd=0,

            activebackground='#16a34a', activeforeground='white'

        )

        self.acc_approve_btn.pack(side=tk.LEFT, padx=2)

        self.acc_reject_btn = tk.Button(

            acc_btn_frame, text='✖ Từ chối',

            command=self.reject_selected_account,

            font=('Segoe UI', 8, 'bold'), bg='#f59e0b', fg='white',

            cursor='hand2', padx=8, relief=tk.FLAT, bd=0,

            activebackground='#d97706', activeforeground='white'

        )

        self.acc_reject_btn.pack(side=tk.LEFT, padx=2)

        self.acc_delete_btn = tk.Button(

            acc_btn_frame, text='🗑 Xóa',

            command=self.delete_selected_account,

            font=('Segoe UI', 8, 'bold'), bg=C_RED, fg='white',

            cursor='hand2', padx=8, relief=tk.FLAT, bd=0,

            activebackground='#dc2626', activeforeground='white'

        )

        self.acc_delete_btn.pack(side=tk.LEFT, padx=2)

        self.acc_edit_btn = tk.Button(

            acc_btn_frame, text='✏ Sửa',

            command=self.edit_selected_account,

            font=('Segoe UI', 8, 'bold'), bg='#8b5cf6', fg='white',

            cursor='hand2', padx=8, relief=tk.FLAT, bd=0,

            activebackground='#7c3aed', activeforeground='white'

        )

        self.acc_edit_btn.pack(side=tk.LEFT, padx=2)

        # Store accounts data

        self._accounts_data = []

        # ===== CONTROL BUTTONS =====

        control_frame = tk.Frame(right_frame, bg=C_PANEL)

        control_frame.pack(side=tk.BOTTOM, pady=(8, 6), padx=8, fill=tk.X)

        self.start_btn = tk.Button(

            control_frame, text='START',

            command=self.start_monitoring,

            font=('Segoe UI', 12, 'bold'), bg=C_GREEN, fg='white',

            relief=tk.FLAT, bd=0, cursor='hand2',

            activebackground='#16a34a', activeforeground='white'

        )

        self.start_btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True, ipady=4)

        self.stop_btn = tk.Button(

            control_frame, text='STOP',

            command=self.stop_monitoring,

            font=('Segoe UI', 12, 'bold'), bg=C_RED, fg='white',

            relief=tk.FLAT, bd=0, cursor='hand2',

            activebackground='#dc2626', activeforeground='white',

            state=tk.DISABLED

        )

        self.stop_btn.pack(side=tk.LEFT, padx=3, fill=tk.X, expand=True, ipady=4)

        self.manual_trigger_btn = tk.Button(

            control_frame, text='MANUAL CLEAN',

            command=self.manual_trigger,

            font=('Segoe UI', 10, 'bold'), bg=C_ORANGE, fg='white',

            relief=tk.FLAT, bd=0, cursor='hand2',

            activebackground='#d97706', activeforeground='white'

        )

        self.manual_trigger_btn.pack(pady=(6, 0), fill=tk.X, ipady=3)

        # ===== FOOTER =====

        footer_frame = tk.Frame(self.root, bg=C_HEADER, height=26)

        footer_frame.pack(fill=tk.X)

        footer_frame.pack_propagate(False)

        self.footer_label = tk.Label(

            footer_frame,

            text=f'Solar Panel Cleaning System v{CONFIG["APP_VERSION"]}  |  Initializing...',

            font=('Segoe UI', 8), bg=C_HEADER, fg=C_TEXT3

        )

        self.footer_label.pack(pady=3)

        # Bind drag-scroll cho bảng điều khiển (sau khi tất cả widget đã tạo xong)

        self.root.after(200, self._bind_drag_to_panel)

    def create_metric(self, parent, title, name, row):

        """Tạo metric display — Industrial style"""

        C = self._colors

        frame = tk.Frame(parent, bg=C['card'],

                         highlightbackground=C['border'], highlightthickness=1)

        frame.grid(row=row, column=0, pady=4, padx=0, sticky='ew')

        tk.Label(frame, text=f'  {title.upper()}', font=('Segoe UI', 9, 'bold'),

                 bg=C['header'], fg=C['text3'], anchor='w').pack(fill=tk.X, ipady=4)

        inner = tk.Frame(frame, bg=C['card'])

        inner.pack(padx=8, pady=6, fill=tk.X)

        value_label = tk.Label(

            inner, text='0.00%',

            font=('Consolas', 18, 'bold'), bg=C['card'], fg=C['cyan']

        )

        value_label.pack(pady=2)

        progress = ttk.Progressbar(

            inner, length=300, mode='determinate', maximum=100,

            style='Cyan.Horizontal.TProgressbar'

        )

        progress.pack(pady=(2, 4), padx=4, fill=tk.X)

        setattr(self, f'{name}_value', value_label)

        setattr(self, f'{name}_bar', progress)

    def create_class_bar(self, parent, label, row):

        """Tạo class probability bar — Industrial style"""

        C = self._colors

        label_widget = tk.Label(

            parent, text=label, font=('Segoe UI', 9, 'bold'),

            bg=C['card'], fg=C['text2']

        )

        label_widget.grid(row=row, column=0, padx=(0, 8), pady=4, sticky='w')

        style_name = 'Red' if label == 'ban' else 'Green' if label == 'sach' else 'Cyan'

        progress = ttk.Progressbar(

            parent, length=180, mode='determinate', maximum=100,

            style=f'{style_name}.Horizontal.TProgressbar'

        )

        progress.grid(row=row, column=1, padx=0, pady=4, sticky='ew')

        value_label = tk.Label(

            parent, text='0%', font=('Consolas', 9, 'bold'),

            bg=C['card'], fg=C['text1'], width=6

        )

        value_label.grid(row=row, column=2, padx=(6, 0), pady=4)

        parent.columnconfigure(1, weight=1)

        self.class_bars[label] = (progress, value_label)

    def initialize_system(self):

        """Khởi tạo hệ thống"""

        self.footer_label.config(text='Initializing TFLite AI model...')

        # Initialize TFLite detector

        self.detector = DirtDetectorTFLite(CONFIG)

        if not self.detector.load_model() or not self.detector.load_labels():

            messagebox.showerror("Error", "Failed to load TFLite model!\n\nFiles needed:\n- model.tflite\n- labels.txt")

            return

        # Initialize YOLOv8 Detect (leaf, bird_drop, crack)

        try:

            from ultralytics import YOLO

            yolo_path = _res('Solar.pt')

            if os.path.exists(yolo_path):

                self.yolo_model = YOLO(yolo_path)

                print(f"✅ Đã tải mô hình YOLOv8 Detect: {yolo_path}")

            else:

                print(f"⚠️ Không tìm thấy mô hình YOLO tại {yolo_path}")

            # Initialize YOLOv8-Seg (nhận diện chính xác tấm pin)

            panel_seg_path = CONFIG.get('PANEL_SEG_MODEL_PATH', _res('panel 2.pt'))

            if os.path.exists(panel_seg_path):

                self.panel_seg_model = YOLO(panel_seg_path)

                print(f"✅ Đã tải mô hình Panel-Seg: {panel_seg_path}")

            else:

                print(f"⚠️ Không tìm thấy mô hình Panel-Seg tại {panel_seg_path}")

        except Exception as e:

            print(f"❌ Lỗi tải YOLOv8: {e}")

        # Initialize PLC

        if CONFIG['PLC']['ENABLED'] and PLC_AVAILABLE:

            self.connect_plc()

        else:

            self.plc_status_label.config(text='DISABLED', fg='#eab308')

            self.footer_label.config(text='PLC control disabled')

        # Initialize camera

        camera_id = int(self.camera_id_var.get())

        self.camera = self._open_camera(camera_id)

        if not self.camera:
            print(f"⚠️ Camera {camera_id} không khả dụng — Vui lòng đổi Camera ID trên giao diện")
            self.footer_label.config(text=f'Camera {camera_id} không khả dụng — Vui lòng chọn camera khác')
        else:
            self.footer_label.config(text=f'System ready | Camera {camera_id} | Press START')


        # Auto-start web server

        self.start_web_server()

        # ☁️ Initialize Cloud API Client

        self._init_cloud_client()

        # ⚡ Initialize Power Monitor (PZEM-017 qua USB trực tiếp)

        try:

            from power_db import PowerMonitor, CleaningEfficiencyTracker

            self.power_monitor = PowerMonitor(CONFIG)

            self.efficiency_tracker = CleaningEfficiencyTracker(self.power_monitor, CONFIG)

            self.power_monitor.start()

            print("⚡ Power Monitor initialized")

        except Exception as e:

            print(f"⚠️ Power Monitor init error: {e}")

            import traceback; traceback.print_exc()

        # 🤖 Initialize Zalo Bot & Smart Notification
        try:
            from zalo_service import zalo_service
            zalo_service.set_system_hooks(
                results_getter=lambda: self.web_module.current_results if self.web_module else {},
                cmd_queue=self.web_module.command_queue if self.web_module else None
            )
            if zalo_service.config.get('enabled', True):
                zalo_service.start()
                print("🤖 Zalo Bot service initialized")
        except Exception as e:
            print(f"⚠️ Zalo Bot init error: {e}")

        # Tự động mở camera preview (chỉ hiển thị, chưa nhận diện AI)
        self.root.after(200, self.start_camera_preview)


    def open_power_window(self):

        """⚡ Mở cửa sổ Power Analysis riêng"""

        if self._power_window and self._power_window.winfo_exists():

            self._power_window.lift()

            self._power_window.focus_force()

            return

        self._power_window = PowerAnalysisWindow(self.root, self.power_monitor, self.efficiency_tracker)

    def _configure_camera_capture(self, camera, camera_id):
        """Apply the requested camera resolution/settings and log the actual values."""
        try:
            target_width = int(CONFIG.get('CAMERA_FRAME_WIDTH', 1920))
            target_height = int(CONFIG.get('CAMERA_FRAME_HEIGHT', 1080))
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)

            if CONFIG.get('DISABLE_AUTOFOCUS', True) and hasattr(cv2, 'CAP_PROP_AUTOFOCUS'):
                try:
                    camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                except Exception:
                    pass

            actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            autofocus_state = None
            if hasattr(cv2, 'CAP_PROP_AUTOFOCUS'):
                try:
                    autofocus_state = camera.get(cv2.CAP_PROP_AUTOFOCUS)
                except Exception:
                    autofocus_state = None

            CONFIG['CAMERA_ID'] = int(camera_id)
            print(f"📷 Camera {camera_id}: requested {target_width}x{target_height}, actual {actual_width}x{actual_height}, autofocus={autofocus_state}")
        except Exception as e:
            print(f"⚠️ Camera configure warning: {e}")

    def _open_camera(self, camera_id):
        """Open camera and apply the industrial capture configuration safely."""
        try:
            camera = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
            if not camera or not camera.isOpened():
                if camera:
                    camera.release()
                camera = cv2.VideoCapture(camera_id)

            if not camera or not camera.isOpened():
                if camera:
                    camera.release()
                print(f"⚠️ Camera {camera_id} không khả dụng.")
                return None

            self._configure_camera_capture(camera, camera_id)
            return camera
        except Exception as e:
            print(f"❌ Camera open error: {e}")
            return None


    def _normalize_frame_orientation(self, frame):

        """Force a portrait frame for vertical solar panels before UI/AI consume it."""

        return apply_frame_rotation(frame, CONFIG)

    def connect_plc(self):

        """Kết nối PLC"""

        self.plc = PLCController(CONFIG)

        if self.plc.connect():

            self.plc_status_label.config(text='CONNECTED', fg='#22c55e')

            self.plc_info_label.config(text=f"IP: {CONFIG['PLC']['IP']} | DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0")

            self.footer_label.config(text=f'PLC connected to {CONFIG["PLC"]["IP"]}')

            return True

        else:

            self.plc_status_label.config(text='CONNECTION FAILED', fg='#ef4444')

            self.footer_label.config(text='PLC connection failed - auto-clean disabled')

            return False

    def reconnect_plc(self):

        """Kết nối lại PLC"""

        if self.is_running:

            messagebox.showwarning("Cảnh báo", "Vui lòng DỪNG giám sát trước khi đổi kết nối PLC!")

            return

        if self.plc and self.plc.is_connected:

            self.plc.disconnect()

        new_ip = self.plc_ip_var.get().strip()

        if not new_ip:

            messagebox.showerror("Lỗi", "Vui lòng nhập địa chỉ IP hợp lệ!")

            return

        parts = new_ip.split('.')

        if len(parts) != 4:

            messagebox.showerror("Lỗi", "Định dạng IP không hợp lệ!\n\nVí dụ: 192.168.1.11")

            return

        try:

            for part in parts:

                num = int(part)

                if num < 0 or num > 255:

                    raise ValueError

        except ValueError:

            messagebox.showerror("Lỗi", "Định dạng IP không hợp lệ!\n\nMỗi số phải từ 0-255")

            return

        CONFIG['PLC']['IP'] = new_ip

        self.footer_label.config(text=f'Connecting PLC {new_ip}...')

        self.plc_status_label.config(text='CONNECTING...', fg='#eab308')

        if self.connect_plc():

            messagebox.showinfo("Thành công", f"✅ Đã kết nối PLC!\n\nIP: {new_ip}\nDB: DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0")

        else:

            messagebox.showerror("Thất bại", f"❌ Kết nối PLC thất bại!\n\nIP: {new_ip}\n\nKiểm tra:\n1. PLC đã bật nguồn chưa\n2. Địa chỉ IP có đúng không\n3. Cùng mạng LAN không\n4. Thử ping: ping {new_ip}")

    def _setup_spin_button(self, btn, var, step, min_val, max_val):

        """HMI-style: click + giữ nút tự lặp (auto-repeat) — chuẩn công nghiệp"""

        repeat_id = [None]

        repeat_delay = [400]  # ms đầu tiên chậm, sau đó nhanh dần

        def do_step():

            try:

                cur = int(var.get())

            except ValueError:

                cur = min_val

            new = max(min_val, min(max_val, cur + step))

            var.set(str(new))

        def on_press(event):

            do_step()

            repeat_delay[0] = 400

            schedule_repeat()

        def schedule_repeat():

            repeat_id[0] = btn.after(repeat_delay[0], on_repeat)

        def on_repeat():

            do_step()

            # Tăng tốc dần (giảm delay tới 50ms)

            repeat_delay[0] = max(50, int(repeat_delay[0] * 0.7))

            schedule_repeat()

        def on_release(event):

            if repeat_id[0] is not None:

                btn.after_cancel(repeat_id[0])

                repeat_id[0] = None

        btn.bind('<ButtonPress-1>', on_press)

        btn.bind('<ButtonRelease-1>', on_release)

    def apply_threshold(self):

        """Áp dụng ngưỡng mới - CHỈ từ Desktop App"""

        try:

            threshold_percent = float(self.dirt_threshold_var.get())

            if threshold_percent < 0 or threshold_percent > 100:

                messagebox.showerror("Lỗi", "Ngưỡng phải trong khoảng 0-100%!")

                return

            threshold_value = threshold_percent / 100.0

            CONFIG['DIRT_AREA_THRESHOLD'] = threshold_value

            self.threshold_info_label.config(

                text=f'Sẽ vệ sinh khi tỷ lệ patch bẩn ≥ {threshold_percent:.0f}%'

            )

            # Sync ngay sang web module → web thấy thay đổi tức thì

            try:

                if self.web_module and hasattr(self.web_module, 'current_results'):

                    self.web_module.current_results['dirt_threshold'] = threshold_value

            except Exception:

                pass

            self.footer_label.config(text=f'Dirty patch threshold: >= {threshold_percent:.0f}%')

            print(f"✅ Threshold updated to {threshold_percent:.0f}% (Desktop only)")

        except ValueError:

            messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ (0-100)!")

    def apply_cnn_threshold(self):

        """Áp dụng ngưỡng phân loại bẩn CNN mới"""

        try:

            threshold_percent = float(self.cnn_threshold_var.get())

            if threshold_percent < 0 or threshold_percent > 100:

                messagebox.showerror("Lỗi", "Ngưỡng phải trong khoảng 0-100%!")

                return

            threshold_value = threshold_percent / 100.0

            CONFIG['CNN_DIRTY_THRESHOLD'] = threshold_value

            self.cnn_threshold_info_label.config(

                text=f'CNN decision threshold: {threshold_percent:.0f}%'

            )

            # Sync ngay sang web module → web thấy thay đổi tức thì

            try:

                if self.web_module and hasattr(self.web_module, 'current_results'):

                    self.web_module.current_results['cnn_dirty_threshold'] = threshold_value

            except Exception:

                pass

            print(f"✅ CNN classification threshold updated to {threshold_percent:.0f}% (Desktop only)")

        except ValueError:

            messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ (0-100)!")

    def apply_snapshot_interval(self):

        """Áp dụng chu kỳ chụp ảnh mới"""

        try:

            interval_minutes = int(self.snapshot_interval_var.get())

            if interval_minutes < 1 or interval_minutes > 1440:  # 1 phút đến 24 giờ

                messagebox.showerror("Lỗi", "Chu kỳ phải trong khoảng 1-1440 phút (1 phút - 24 giờ)!")

                return

            interval_seconds = interval_minutes * 60

            CONFIG['SNAPSHOT_INTERVAL'] = interval_seconds

            self.interval_info_label.config(

                text=f'AI chạy mỗi {interval_minutes} phút'

            )

            # Sync ngay sang web module → web thấy thay đổi tức thì

            try:

                if self.web_module and hasattr(self.web_module, 'current_results'):

                    self.web_module.current_results['snapshot_interval'] = interval_seconds

            except Exception:

                pass

            self.footer_label.config(text=f'AI interval: {interval_minutes} min')

            print(f"✅ Snapshot interval updated to {interval_minutes} minutes")

        except ValueError:

            messagebox.showerror("Lỗi", "Vui lòng nhập số nguyên hợp lệ (1-1440)!")

    def switch_camera(self):

        """Đổi camera - Hot-swap an toàn với lock"""

        camera_id = int(self.camera_id_var.get())

        # Tạo camera mới trước

        new_camera = self._open_camera(camera_id)

        if not new_camera:

            messagebox.showerror("Lỗi", f"Không mở được Camera {camera_id}!\n\nCamera này không khả dụng.")

            return

        # Hot-swap với lock

        with self.camera_lock:

            # Release camera cũ

            if self.camera:

                self.camera.release()

                time.sleep(0.1)  # Đợi camera release hoàn toàn

            # Gán camera mới

            self.camera = new_camera

            # Đồng bộ camera mới với Web server (nếu đang chạy)

            if self.web_server_running and self.web_module:

                try:

                    self.web_module.camera = self.camera  # Update Web's camera reference

                    print(f"✅ Desktop → Web: Camera synced to ID {camera_id}")

                except Exception as e:

                    print(f"⚠️  Web camera sync warning: {e}")

        # Thông báo thành công

        if self.is_running:

            print(f"✅ Camera switched to {camera_id} (hot-swap while running)")

        else:

            self.footer_label.config(text=f'Camera {camera_id} ready')

            messagebox.showinfo("Thành công", f"✅ Đã chuyển sang Camera {camera_id}\n\nHệ thống sẵn sàng!")

            # Khởi động lại camera preview nếu chưa chạy AI

            if not self.camera_preview_running:

                self.start_camera_preview()

    def start_camera_preview(self):
        """Bật camera preview — chỉ hiển thị video realtime, KHÔNG chạy AI nhận diện."""
        if self.camera_preview_running:
            return
        if not self.camera or not self.camera.isOpened():
            print("⚠️ Camera chưa sẵn sàng, không thể mở preview.")
            return

        self.camera_preview_running = True
        try:
            self.footer_label.config(text='📹 Camera đang hoạt động — Nhấn START để bắt đầu nhận diện AI')
        except Exception:
            pass
        self._preview_thread = threading.Thread(target=self._camera_preview_loop, daemon=True)
        self._preview_thread.start()
        print("📹 Camera preview started (chỉ hiển thị, chưa nhận diện AI)")

    def _camera_preview_loop(self):
        """Vòng lặp camera preview — hiển thị video realtime, không chạy AI."""
        while self.camera_preview_running and not self.is_running:
            try:
                with self.camera_lock:
                    if not self.camera or not self.camera.isOpened():
                        time.sleep(0.1)
                        continue
                    ret, frame = self.camera.read()

                if not ret:
                    time.sleep(0.1)
                    continue

                frame = self._normalize_frame_orientation(frame)

                # Lưu frame cho Web server
                self._last_frame = frame.copy()

                # Hiển thị video lên UI (không chạy AI)
                self.update_live_video_ui(frame)

                time.sleep(0.033)  # ~30 FPS

            except Exception as e:
                print(f"❌ Preview error: {e}")
                time.sleep(0.1)

        print("📹 Camera preview loop stopped.")


    def stop_camera_preview(self):

        """Dừng camera preview loop."""

        self.camera_preview_running = False

    def start_monitoring(self):

        """Bắt đầu giám sát + nhận diện AI"""

        if not self.is_running:

            if not self.camera or not self.camera.isOpened():

                messagebox.showerror("Lỗi", "Camera không khả dụng!")

                return

            # Dừng preview loop trước khi bắt đầu AI monitoring

            self.stop_camera_preview()

            time.sleep(0.1)  # Chờ preview thread dừng hẳn

            self.is_running = True

            self.start_time = time.time()

            self.total_frames = 0

            self.cleaning_count = 0

            self.start_btn.config(state=tk.DISABLED)

            self.stop_btn.config(state=tk.NORMAL)

            self.video_thread = threading.Thread(target=self.update_frame, daemon=True)

            self.video_thread.start()

            # Hiển thị thông báo tùy theo mode

            if CONFIG.get('SNAPSHOT_MODE', False):

                interval_min = CONFIG.get('SNAPSHOT_INTERVAL', 600) // 60

                self.footer_label.config(text=f'🤖 AI đang nhận diện — Snapshot mode — every {interval_min} min')

            else:

                self.footer_label.config(text='🤖 AI đang nhận diện — Video mode — auto-clean enabled')

    def stop_monitoring(self):

        """Dừng giám sát AI và quay lại camera preview"""

        self.is_running = False

        self.start_btn.config(state=tk.NORMAL)

        self.stop_btn.config(state=tk.DISABLED)

        self.detection_start_time = None

        self.last_detected_class = None

        self.is_detection_confirmed = False

        self.footer_label.config(text='AI đã dừng — Camera preview đang hoạt động')

        # Quay lại camera preview (chỉ hiển thị, không AI)

        self.root.after(300, self.start_camera_preview)

    def manual_trigger(self):

        """Kích PLC thủ công"""

        if not self.plc or not self.plc.is_connected:

            messagebox.showwarning("PLC Chưa Kết Nối", "Không thể kích - PLC chưa kết nối!")

            return

        if messagebox.askyesno("Vệ Sinh Thủ Công", "Kích PLC ngay bây giờ?"):

            success = self.plc.trigger_cleaning()

            if success:

                self.cleaning_count += 1

                self.cleaning_label.config(text=f'Cleaned: {self.cleaning_count}')

                if self.efficiency_tracker:

                    self.efficiency_tracker.on_cleaning_started(

                        trigger_reason='Manual Clean (Desktop)',

                        dirty_ratio=0.0,

                        ai_label='Manual',

                        ai_confidence=1.0,

                    )

                messagebox.showinfo("Thành công", "✅ PLC đã được kích!\n\nDB1.DBX0.0: 1 → 0")

            else:

                messagebox.showerror("Thất bại", "❌ Kích PLC thất bại!")

    def update_frame(self):

        """Hiển thị video real-time + AI mỗi 10 phút"""

        print(" Video monitoring + AI snapshot mode")

        self.update_frame_hybrid_mode()

    def update_frame_hybrid_mode(self):

        """

        CHẾ ĐỘ MỚI: Hiển thị video real-time để giám sát

        Nhưng CHỈ chạy AI + lưu ảnh mỗi 10 phút

        """

        print(" Hybrid mode started: Video monitoring + AI snapshot every 10 min")

        # Tạo thư mục lưu ảnh

        if CONFIG.get('SAVE_SNAPSHOTS', True):

            os.makedirs(CONFIG.get('SNAPSHOT_FOLDER', 'snapshots'), exist_ok=True)

        snapshot_interval = CONFIG.get('SNAPSHOT_INTERVAL', 600)

        last_snapshot_time = 0

        frame_count = 0

        while self.is_running:

            try:

                current_time = time.time()

                # ĐỌC VIDEO LIÊN TỤC để hiển thị

                with self.camera_lock:

                    if not self.camera or not self.camera.isOpened():

                        print("❌ Camera lost!")

                        time.sleep(0.1)

                        continue

                    ret, frame = self.camera.read()

                if not ret:

                    time.sleep(0.1)

                    continue

                frame = self._normalize_frame_orientation(frame)

                frame_count += 1

                # Tính thời gian còn lại đến lần chụp tiếp theo

                time_since_last_snapshot = current_time - last_snapshot_time

                remaining = max(0, snapshot_interval - time_since_last_snapshot)

                minutes = int(remaining // 60)

                seconds = int(remaining % 60)

                # KIỂM TRA: Đã đến lúc chạy AI chưa?

                run_ai_now = (time_since_last_snapshot >= snapshot_interval)

                if run_ai_now:

                    # ========== CHẠY AI + LƯU ẢNH (mỗi 10 phút) ==========

                    print(f"\n🤖 Đang chạy AI phân tích...")

                    # Lưu ảnh

                    if CONFIG.get('SAVE_SNAPSHOTS', True):

                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

                        filename = f"{timestamp}.jpg"

                        snapshot_folder = CONFIG.get('SNAPSHOT_FOLDER', 'snapshots')

                        filepath = os.path.join(snapshot_folder, filename)

                        cv2.imwrite(filepath, frame)

                        print(f"💾 Đã lưu: {filepath}")

                        # Lưu thông tin snapshot để web hiển thị

                        self._last_snapshot_filename = filename

                        self._last_snapshot_time = datetime.now().strftime('%H:%M:%S')

                        self._last_snapshot_timestamp = time.time()

                        # Kiểm tra và xóa ảnh cũ nếu vượt 1GB

                        cleanup_old_snapshots(snapshot_folder, max_size_gb=1.0)

                    # ========== YOLO DETECT: lá cây, phân chim, vết nứt ==========

                    yolo_results = None

                    yolo_clean_faults = []  # Lá cây, phân chim (Kích PLC vệ sinh)

                    yolo_crack_faults = []  # Nứt vỡ (Chỉ hiện cảnh báo)

                    if self.yolo_model is not None:
                        try:
                            res = self.yolo_model(frame, verbose=False, conf=0.25, device='cpu')[0]
                            yolo_results = res
                            for box in res.boxes:
                                cls_id = int(box.cls[0].item() if hasattr(box.cls[0], 'item') else box.cls[0])
                                conf_val = float(box.conf[0].item() if hasattr(box.conf[0], 'item') else box.conf[0])
                                cname = res.names[cls_id].lower()
                                # Chỉ xử lý lá cây, phân chim, vết nứt (bỏ class normal)
                                if conf_val > 0.4:
                                    if cname in ['leaf', 'lá cây', 'bird_drop', 'phân chim']:
                                        yolo_clean_faults.append(cname)
                                    elif cname in ['crack', 'nứt vỡ']:
                                        yolo_crack_faults.append(cname)
                        except Exception as e:
                            print(f"❌ YOLOv8 Detect Error: {e}")

                    # ========== PANEL SEGMENTATION (panel 2.pt) ==========
                    panel_mask_binary = None
                    panel_bbox = None
                    if self.panel_seg_model is not None:
                        try:
                            seg_res = self.panel_seg_model(frame, verbose=False, conf=0.3, device='cpu')[0]


                            if seg_res.masks is not None and len(seg_res.masks) > 0:

                                # Lấy mask có diện tích lớn nhất (tấm pin chính)

                                best_idx = 0

                                best_area = 0

                                for mi, m in enumerate(seg_res.masks.data):

                                    area = float(m.sum().item()) if hasattr(m.sum(), 'item') else float(m.sum())

                                    if area > best_area:

                                        best_area = area

                                        best_idx = mi

                                # Tạo binary mask ở kích thước frame gốc

                                mask_tensor = seg_res.masks.data[best_idx]

                                mask_np = mask_tensor.cpu().numpy() if hasattr(mask_tensor, 'cpu') else np.array(mask_tensor)

                                h_f, w_f = frame.shape[:2]

                                panel_mask_binary = cv2.resize(mask_np, (w_f, h_f), interpolation=cv2.INTER_NEAREST)

                                panel_mask_binary = (panel_mask_binary > 0.5).astype(np.uint8)

                                # Tính bbox từ mask

                                ys, xs = np.where(panel_mask_binary > 0)

                                if len(xs) > 0 and len(ys) > 0:

                                    px1, py1 = int(xs.min()), int(ys.min())

                                    px2, py2 = int(xs.max()), int(ys.max())

                                    panel_bbox = (px1, py1, px2, py2)

                                    print(f"✂️ Panel-Seg: bbox ({px1},{py1})-({px2},{py2}), mask_area={best_area:.0f}px")

                        except Exception as e:

                            print(f"❌ Panel-Seg Error: {e}")

                            traceback.print_exc()

                    # ========== QUYẾT ĐỊNH CHẠY CNN ==========

                    has_panel = panel_bbox is not None

                    no_panel = not has_panel and (self.panel_seg_model is not None)

                    if no_panel:

                        # --- KHÔNG CÓ TẤM PIN: Bỏ qua CNN ---

                        print(f"⚪ Panel-Seg: Không phát hiện tấm pin. Bỏ qua CNN.")

                        label_name = 'no_panel'

                        confidence = 1.0

                        area_ratio = 0.0

                        pred_probs = np.array([0.0, 0.0], dtype=np.float32)

                        p_dirty = 0.0

                        pred_class = -1

                        mask = None

                    else:

                        # --- CÓ TẤM PIN: Crop theo seg mask và chạy CNN ---

                        panel_roi_mask = None

                        if has_panel:

                            px1, py1, px2, py2 = panel_bbox
                            h_f, w_f = frame.shape[:2]
                            pad_x = int((px2 - px1) * float(CONFIG.get('PANEL_CROP_PADDING', 0.0)))
                            pad_y = int((py2 - py1) * float(CONFIG.get('PANEL_CROP_PADDING', 0.0)))
                            cx1 = max(0, px1 - pad_x)
                            cy1 = max(0, py1 - pad_y)
                            cx2 = min(w_f, px2 + pad_x)
                            cy2 = min(h_f, py2 + pad_y)

                            # Crop tấm pin theo bbox của mask

                            cnn_input = frame[cy1:cy2, cx1:cx2].copy()

                            if cnn_input.size == 0:

                                cnn_input = frame

                            else:

                                # Mask chỉ dùng khi bật chế độ thử nghiệm. Mặc định không tô đen
                                # nền vì làm lệch phân phối ảnh so với dữ liệu train/test CNN.

                                panel_roi_mask = panel_mask_binary[cy1:cy2, cx1:cx2]

                                if CONFIG.get('MASK_BACKGROUND_FOR_CNN', False):

                                    cnn_input = cv2.bitwise_and(cnn_input, cnn_input, mask=panel_roi_mask)

                            print(f"✂️ Crop tấm pin (Seg): ({cx1},{cy1})-({cx2},{cy2}) → CNN")

                        else:

                            cnn_input = frame  # fallback: không có panel seg model

                            print(f"⚠️ Panel-Seg chưa tải, dùng full frame cho CNN")

                        cnn_mask = panel_roi_mask if (
                            has_panel and CONFIG.get('USE_PANEL_PERSPECTIVE_WARP', False)
                        ) else None

                        p_dirty, pred_class, label_name, pred_probs, confidence = self.detector.predict(cnn_input, mask=cnn_mask)

                        area_ratio, mask = self.detector.compute_dirt_ratio(cnn_input)

                    # Lưu confidence để web sử dụng

                    self._last_confidence = confidence

                    self._last_cnn_active = not no_panel

                    self._last_panel_detected = bool(has_panel)

                    self._last_yolo_clean_faults = sorted(set(yolo_clean_faults))

                    self._last_yolo_crack_faults = sorted(set(yolo_crack_faults))

                    # Get config

                    trigger_class = CONFIG['TRIGGER_CLASS'].lower()

                    min_confidence = CONFIG.get('MIN_CONFIDENCE', 0.60)

                    print(f"🔍 Panel-Seg={has_panel} | YOLO: Clean_faults={yolo_clean_faults}, Crack={yolo_crack_faults}")

                    if not no_panel:

                        print(f"🔍 CNN: Class={label_name}, Conf={confidence*100:.1f}%, Bẩn={area_ratio*100:.1f}%")

                    # ========== QUYẾT ĐỊNH VỆ SINH & CẢNH BÁO ==========

                    should_clean = False

                    has_crack = len(yolo_crack_faults) > 0

                    trigger_reasons = []

                    if no_panel:

                        # Không có tấm pin: không vệ sinh

                        print(f"⚪ KHÔNG CÓ TẤM PIN - Bỏ qua toàn bộ")

                    else:

                        # Xác định lỗi cần VỆ SINH

                        has_dirt = False

                        if (trigger_class in label_name.lower() and

                                confidence >= min_confidence and

                                area_ratio >= CONFIG['DIRT_AREA_THRESHOLD']):

                            should_clean = True

                            has_dirt = True

                            trigger_reasons.append("Bụi (CNN)")

                        has_leaf = False

                        has_bird_drop = False

                        if yolo_clean_faults:

                            should_clean = True

                            trigger_reasons.append(f"Vật cản: {', '.join(set(yolo_clean_faults))} (YOLO)")

                            for fault in yolo_clean_faults:

                                if fault in ['leaf', 'lá cây']: has_leaf = True

                                if fault in ['bird_drop', 'phân chim']: has_bird_drop = True

                        # Xử lý PLC

                        if should_clean:

                            print(f"🧹 CẦN VỆ SINH ({' | '.join(trigger_reasons)})! Kích PLC...")

                            if self.plc and self.plc.is_connected:

                                success = self.plc.trigger_faults(has_dirt=has_dirt, has_leaf=has_leaf, has_bird_drop=has_bird_drop)

                                if success:

                                    self.cleaning_count += 1

                                    print(f"✅ Để KÍCH PLC! Tổng: {self.cleaning_count}")

                                    # ⚡ Theo dõi hiệu suất vệ sinh

                                    if self.efficiency_tracker:

                                        self.efficiency_tracker.on_cleaning_started(

                                            trigger_reason=' | '.join(trigger_reasons),

                                            dirty_ratio=float(area_ratio),

                                            ai_label=label_name,

                                            ai_confidence=float(confidence),

                                        )

                                else:

                                    print(f"❌ PLC trigger failed!")

                        else:

                            print(f"✅ SẠCH (Không cần vệ sinh)")

                        if has_crack:

                            print(f"🚨 PHÁT HIỆN NỨT VỠ TẤM PIN! Cần bảo trì khẩn cấp!")

                        # 📱 Gửi Cảnh báo tự động qua Zalo Bot (Bụi bẩn, Lá cây, Phân chim, Nứt vỡ)
                        try:
                            from zalo_service import zalo_service
                            cur_power = float(getattr(self.power_monitor, 'last_power', 0.0) if hasattr(self, 'power_monitor') and self.power_monitor else 0.0)
                            plc_trig = bool(self.plc and self.plc.is_connected)

                            if has_dirt:
                                dirty_cnt = int(getattr(self.detector, 'last_analysis', {}).get('dirty_patch_count', 0))
                                valid_cnt = int(getattr(self.detector, 'last_analysis', {}).get('valid_patch_count', 32))
                                zalo_service.notify_dirt_detected(
                                    area_ratio=float(area_ratio),
                                    dirty_patches=dirty_cnt,
                                    total_patches=valid_cnt,
                                    power_watts=cur_power,
                                    plc_triggered=plc_trig
                                )

                            if yolo_clean_faults:
                                zalo_service.notify_debris_detected(
                                    debris_list=yolo_clean_faults,
                                    area_ratio=float(area_ratio),
                                    plc_triggered=plc_trig
                                )

                            if has_crack:
                                zalo_service.notify_crack_detected(crack_list=yolo_crack_faults)
                        except Exception as ez:
                            print(f"⚠️ [Zalo Notification Error]: {ez}")

                    # Cập nhật UI với kết quả AI


                    self.update_snapshot_ui(frame, label_name, confidence, area_ratio, pred_probs, mask, should_clean, yolo_results, has_crack, no_panel, panel_mask_binary)

                    # Lưu kết quả cho Web

                    self._last_p_dirty = float(p_dirty) if not no_panel else 0.0

                    self._last_area_ratio = float(area_ratio)

                    self._last_label_name = label_name

                    self._last_pred_probs = pred_probs

                    self._last_pred_class = int(pred_class) if pred_class is not None and pred_class != -1 else -1

                    self._last_dirty_patch_count = int(getattr(self.detector, 'last_analysis', {}).get('dirty_patch_count', 0))

                    self._last_valid_patch_count = int(getattr(self.detector, 'last_analysis', {}).get('valid_patch_count', 0))

                    self._last_nopanel_patch_count = 0

                    self._last_frame = frame.copy()

                    self.last_detected_class = label_name

                    # Reset timer

                    last_snapshot_time = current_time

                    print(f"⏰ AI hoàn thành. Chạy lại sau {snapshot_interval//60} phút.\n")

                else:

                    # ========== CHỈ HIỂN THỊ VIDEO (không chạy AI) ==========

                    # Lưu frame cho Web server (cập nhật liên tục)

                    self._last_frame = frame.copy()

                    # Tạo frame hiển thị đơn giản

                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    disp = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

                    # Overlay thông tin countdown

                    countdown_text = f"AI chay sau: {minutes:02d}:{seconds:02d}"

                    cv2.putText(disp, "GIAM SAT REAL-TIME", (10, 30),

                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                    cv2.putText(disp, countdown_text, (10, 70),

                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                    # Hiển thị kết quả AI lần trước (nếu có)

                    if hasattr(self, '_last_label_name') and self._last_label_name:

                        status_text = f"Lan truoc: {self._last_label_name}"

                        cv2.putText(disp, status_text, (10, 110),

                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)

                    # Cập nhật UI với video live

                    self.update_live_video_ui(disp)

                    # Cập nhật countdown label

                    countdown_label_text = f"⏭️ AI chạy sau: {minutes:02d}:{seconds:02d}"

                    self.root.after(0, lambda: self.countdown_label.config(text=countdown_label_text))

                # In log mỗi 30 giây

                if int(remaining) % 30 == 0 and frame_count % 30 == 0:

                    print(f"📹 Đang giám sát... AI chạy sau {minutes:02d}:{seconds:02d}")

                # Sleep ngắn để giảm CPU (30 FPS)

                time.sleep(0.033)

            except Exception as e:

                print(f"❌ Error: {e}")

                traceback.print_exc()

                time.sleep(0.1)

    def _apply_live_frame(self, img):
        """Chạy trong main thread của Tkinter để gán ảnh lên canvas an toàn."""
        try:
            if hasattr(self, 'video_canvas') and self.video_canvas and self.video_canvas.winfo_exists():
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_canvas.configure(image=imgtk)
                self.video_canvas.imgtk = imgtk
        except Exception:
            pass
        finally:
            self._is_rendering_frame = False

    def update_live_video_ui(self, frame):
        """
        Cập nhật UI với video real-time (KHÔNG chạy AI)
        Chỉ hiển thị video để giám sát — Thread-safe, non-blocking
        """
        try:
            if not self.root or getattr(self, '_is_rendering_frame', False):
                return

            self._is_rendering_frame = True

            # Convert và resize image trong worker thread
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)

            canvas_width = 0
            canvas_height = 0
            try:
                if self.video_canvas and self.video_canvas.winfo_exists():
                    canvas_width = self.video_canvas.winfo_width()
                    canvas_height = self.video_canvas.winfo_height()
            except Exception:
                pass

            if canvas_width > 10 and canvas_height > 10:
                img_width, img_height = img.size
                ratio = min(canvas_width / img_width, canvas_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                if new_width > 0 and new_height > 0:
                    img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)

            # Đẩy ảnh sang main GUI thread để update canvas
            self.root.after(0, self._apply_live_frame, img)

        except Exception as e:
            self._is_rendering_frame = False


    def update_ui(self, frame, p_dirty, area_ratio, label_name, pred_probs):

        """Cập nhật giao diện - Tối ưu để giảm chớp nháy"""

        try:

            # Convert và resize image

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(frame_rgb)

            # Lấy kích thước canvas

            canvas_width = self.video_canvas.winfo_width()

            canvas_height = self.video_canvas.winfo_height()

            # Chỉ resize nếu canvas đã render

            if canvas_width > 10 and canvas_height > 10:

                img_width, img_height = img.size

                ratio = min(canvas_width / img_width, canvas_height / img_height)

                new_width = int(img_width * ratio)

                new_height = int(img_height * ratio)

                if new_width > 0 and new_height > 0:

                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Tạo PhotoImage và giữ reference để tránh garbage collection

            imgtk = ImageTk.PhotoImage(image=img)

            # Update image - dùng itemconfig nếu có thể để mượt hơn

            self.video_canvas.configure(image=imgtk)

            self.video_canvas.imgtk = imgtk  # Giữ reference

            # CHỈ update status nếu thay đổi - 2 TRẠNG THÁI (ẩn "nopanel")

            if label_name == CONFIG['TRIGGER_CLASS']:  # "ban"

                new_status = "NEEDS CLEANING"

                new_color = '#ef4444'

            else:

                new_status = "CLEAN"

                new_color = '#22c55e'

            if not hasattr(self, '_last_status') or self._last_status != new_status:

                self.status_frame.config(bg=new_color, highlightbackground=new_color)

                self.status_label.config(text=new_status, bg=new_color)

                self.class_label.config(text=f'Detected: {label_name}', bg=new_color)

                self.countdown_label.config(bg=new_color)

                self._last_status = new_status

            # Update metrics - ít thay đổi hơn

            area_percent = area_ratio * 100

            self.dirt_prob_value.config(text=f'{area_percent:.1f}%')

            self.dirt_prob_bar['value'] = min(100, area_percent)

            # CHỈ HIỂN THỊ 2 CLASS: ban và nopanel (bỏ sach)

            # pred_probs có 3 giá trị: [sach, ban, nopanel] (sau khi đổi labels)

            if len(pred_probs) >= 3:

                # ban = index 1, nopanel = index 2

                display_data = [

                    ('ban', pred_probs[1] * 100),

                    ('nopanel', pred_probs[2] * 100)

                ]

                for label, prob in display_data:

                    if label in self.class_bars:

                        bar, value_label = self.class_bars[label]

                        bar['value'] = prob

                        value_label.config(text=f'{prob:.1f}%')

            # Update stats ít hơn

            elapsed = time.time() - self.start_time

            fps = self.total_frames / elapsed if elapsed > 0 else 0

            self.fps_label.config(text=f'FPS: {fps:.1f}')

            self.frames_label.config(text=f'Frames: {self.total_frames}')

            self.cleaning_label.config(text=f'Cleaned: {self.cleaning_count}')

        except Exception as e:

            print(f"UI update error: {e}")

    def update_snapshot_ui(self, frame, label_name, confidence, area_ratio, pred_probs, mask, should_clean, yolo_results=None, has_crack=False, no_panel=False, panel_mask_binary=None):
        """Cập nhật UI cho chế độ snapshot (Thread-safe)"""
        try:
            # Tạo visualization frame (cho CNN)
            if hasattr(mask, 'ndim') and mask.ndim == 3:
                combined = mask.copy()
            elif mask is None:
                h_f, w_f = frame.shape[:2]
                combined = np.zeros((h_f, w_f, 3), dtype=np.uint8)
                combined[:] = (30, 30, 30)
                cy = h_f // 2
                cv2.putText(combined, "CNN: KHONG CHAY", (20, cy - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 200, 255), 3)
                cv2.putText(combined, "(Khong co tam pin)", (20, cy + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (180, 180, 180), 2)
            else:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                disp = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                mask_color = cv2.applyColorMap(mask.astype(np.uint8), cv2.COLORMAP_JET)
                combined = cv2.addWeighted(disp, 0.7, mask_color, 0.3, 0)

            # Tạo visualization frame cho YOLO
            yolo_img = frame.copy()

            if panel_mask_binary is not None:
                overlay = yolo_img.copy()
                overlay[panel_mask_binary > 0] = (0, 255, 0)
                yolo_img = cv2.addWeighted(yolo_img, 0.7, overlay, 0.3, 0)
                contours, _ = cv2.findContours(panel_mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(yolo_img, contours, -1, (0, 255, 0), 2)

            if yolo_results is not None and hasattr(yolo_results, 'boxes') and yolo_results.boxes is not None:
                for box in yolo_results.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls_id = int(box.cls[0].item() if hasattr(box.cls[0], 'item') else box.cls[0])
                    conf = float(box.conf[0].item() if hasattr(box.conf[0], 'item') else box.conf[0])
                    cname = yolo_results.names[cls_id].lower()
                    if cname in ['panel', 'tấm pin', 'normal']:
                        continue
                    color = (255, 0, 255)
                    if cname in ['leaf', 'lá cây']: color = (0, 255, 0)
                    elif cname in ['bird_drop', 'phân chim']: color = (0, 255, 255)
                    elif cname in ['crack', 'nứt vỡ']: color = (0, 0, 255)

                    cv2.rectangle(yolo_img, (x1, y1), (x2, y2), color, 3)
                    label_text = f"{cname} {conf:.2f}"
                    cv2.putText(yolo_img, label_text, (x1, max(10, y1 - 10)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            analysis = getattr(self.detector, 'last_analysis', {})
            dirty_patch_count = int(analysis.get('dirty_patch_count', 0))
            valid_patch_count = int(analysis.get('valid_patch_count', 0))
            nopanel_patch_count = int(analysis.get('nopanel_patch_count', 0))

            self._last_cnn_patch_frame = combined.copy()
            self._last_yolo_panel_frame = yolo_img.copy()

            if should_clean:
                cv2.rectangle(combined, (0, combined.shape[0]-80), (combined.shape[1], combined.shape[0]), (0, 0, 255), -1)
                cv2.putText(combined, "CAN VE SINH!", (20, combined.shape[0]-30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)

            # Ghép hai ảnh
            h_cnn, w_cnn = combined.shape[:2]
            h_yolo, w_yolo = yolo_img.shape[:2]
            new_w_yolo = int(w_yolo * (h_cnn / float(h_yolo))) if h_yolo > 0 else w_yolo
            yolo_resized = cv2.resize(yolo_img, (new_w_yolo, h_cnn)) if (new_w_yolo > 0 and h_cnn > 0) else yolo_img
            final_display = np.hstack((combined, yolo_resized))

            # Resize anh chuan bi PhotoImage
            frame_rgb = cv2.cvtColor(final_display, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
            try:
                canvas_width = self.video_canvas.winfo_width() if self.video_canvas else 0
                canvas_height = self.video_canvas.winfo_height() if self.video_canvas else 0
            except Exception:
                canvas_width, canvas_height = 0, 0

            if canvas_width > 1 and canvas_height > 1:
                img.thumbnail((canvas_width - 20, canvas_height - 20), Image.Resampling.BILINEAR)

            snapshot_time = datetime.now().strftime('%H:%M:%S')
            area_percent = area_ratio * 100

            def _apply_snapshot_main():
                try:
                    if self.video_canvas and self.video_canvas.winfo_exists():
                        imgtk = ImageTk.PhotoImage(image=img)
                        self.video_canvas.configure(image=imgtk)
                        self.video_canvas.imgtk = imgtk

                    if no_panel:
                        self.status_frame.config(bg='#ca8a04', highlightbackground='#ca8a04')
                        self.status_label.config(text="⚪ KHONG CO TAM PIN", bg='#ca8a04', font=('Segoe UI Semibold', 16))
                        self.class_label.config(text="YOLO khong phat hien tam pin nao trong khung hinh", bg='#ca8a04')
                        self.countdown_label.config(bg='#ca8a04')
                    elif has_crack:
                        self.status_frame.config(bg='#b91c1c', highlightbackground='#b91c1c')
                        self.status_label.config(text="⚠️ CANH BAO NUT VO ⚠️", bg='#b91c1c', font=('Segoe UI', 15, 'bold'))
                        self.class_label.config(text="Yeu cau bao tri ngay lap tuc!", bg='#b91c1c')
                        self.countdown_label.config(bg='#b91c1c')
                    elif valid_patch_count < int(CONFIG.get('MIN_VALID_PATCHES', 10)):
                        self.status_frame.config(bg='#f59e0b', highlightbackground='#f59e0b')
                        self.status_label.config(text="INSUFFICIENT PANEL", bg='#f59e0b', font=('Segoe UI Semibold', 16))
                        self.class_label.config(text=f"Dirty patches: {dirty_patch_count}/{valid_patch_count} | No-panel: {nopanel_patch_count}", bg='#f59e0b')
                        self.countdown_label.config(bg='#f59e0b')
                    elif should_clean:
                        self.status_frame.config(bg='#ef4444', highlightbackground='#ef4444')
                        self.status_label.config(text="NEEDS CLEANING", bg='#ef4444', font=('Segoe UI', 18, 'bold'))
                        self.class_label.config(text=f"Detected: {label_name} ({confidence*100:.1f}%) | Dirty patches: {dirty_patch_count}/{valid_patch_count}", bg='#ef4444')
                        self.countdown_label.config(bg='#ef4444')
                    else:
                        self.status_frame.config(bg='#22c55e', highlightbackground='#22c55e')
                        self.status_label.config(text="CLEAN", bg='#22c55e', font=('Segoe UI', 18, 'bold'))
                        self.class_label.config(text=f"Detected: {label_name} ({confidence*100:.1f}%) | Dirty patches: {dirty_patch_count}/{valid_patch_count}", bg='#22c55e')
                        self.countdown_label.config(bg='#22c55e')

                    self.dirt_prob_value.config(text=f'{area_percent:.1f}%')
                    self.dirt_prob_bar['value'] = min(100, area_percent)

                    display_data = [
                        ('ban', float(pred_probs[1]) * 100),
                        ('sach', float(pred_probs[0]) * 100),
                    ]
                    for lbl, prob in display_data:
                        if lbl in self.class_bars:
                            bar, value_label = self.class_bars[lbl]
                            bar['value'] = prob
                            value_label.config(text=f'{prob:.1f}%')

                    self.cleaning_label.config(text=f'Cleaned: {self.cleaning_count}')
                    self.frames_label.config(text=f'Captured: {snapshot_time}')
                    interval_min = CONFIG.get('SNAPSHOT_INTERVAL', 600) // 60
                    self.fps_label.config(text=f'Interval: {interval_min} min')

                    self.update_snapshot_preview(final_display, label_name, confidence, snapshot_time)
                except Exception as ex:
                    print(f"Error in _apply_snapshot_main: {ex}")

            self.root.after(0, _apply_snapshot_main)

        except Exception as e:
            print(f"Snapshot UI update error: {e}")
            traceback.print_exc()

    def update_snapshot_preview(self, snapshot_frame, label_name, confidence, snapshot_time):
        """Cap nhat anh snapshot vao panel preview (Thread-safe)"""
        try:
            frame_rgb = cv2.cvtColor(snapshot_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)

            canvas_width = 0
            canvas_height = 0
            if self.snapshot_canvas and self.snapshot_canvas.winfo_exists():
                canvas_width = self.snapshot_canvas.winfo_width()
                canvas_height = self.snapshot_canvas.winfo_height()

            if canvas_width > 10 and canvas_height > 10:
                img_width, img_height = img.size
                ratio = min(canvas_width / img_width, canvas_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                if new_width > 0 and new_height > 0:
                    img = img.resize((new_width, new_height), Image.Resampling.BILINEAR)

            if hasattr(self, 'snapshot_canvas') and self.snapshot_canvas and self.snapshot_canvas.winfo_exists():
                imgtk = ImageTk.PhotoImage(image=img)
                self.snapshot_canvas.configure(image=imgtk, text='')
                self.snapshot_canvas.imgtk = imgtk
                self.snapshot_info_label.config(text=f"🕒 {snapshot_time} | {label_name} ({confidence*100:.1f}%)", fg='#f39c12')
        except Exception as e:
            pass

        # ==================== QUẢN LÝ TÀI KHOẢN ====================

    def _get_accounts_file(self):

        """Đường dẫn file accounts.json"""

        return _runtime_path('taikhoan', 'accounts.json')

    def _load_accounts_local(self):

        """Load accounts từ file JSON"""

        try:

            path = self._get_accounts_file()

            if os.path.exists(path):

                with open(path, 'r', encoding='utf-8') as f:

                    data = json.load(f)

                    return data.get('accounts', [])

        except Exception as e:

            print(f"❌ Load accounts error: {e}")

        return []

    def _save_accounts_local(self, accounts):

        """Save accounts ra file JSON"""

        try:

            path = self._get_accounts_file()

            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:

                json.dump({'accounts': accounts}, f, ensure_ascii=False, indent=2)

        except Exception as e:

            print(f"❌ Save accounts error: {e}")

    def refresh_accounts(self):

        """Tải lại danh sách tài khoản và hiển thị"""

        accounts = self._load_accounts_local()

        self._accounts_data = accounts

        self.account_listbox.delete(0, tk.END)

        pending_count = 0

        approved_count = 0

        for acc in accounts:

            status = acc.get('status', 'pending')

            username = acc.get('username', '???')

            fullname = acc.get('fullname', '')

            if status == 'pending':

                icon = '⏳'

                pending_count += 1

            elif status == 'approved':

                icon = '✅'

                approved_count += 1

            elif status == 'rejected':

                icon = '❌'

            else:

                icon = '❓'

            display = f"{icon} {username}"

            if fullname:

                display += f" ({fullname})"

            display += f" [{status}]"

            self.account_listbox.insert(tk.END, display)

            # Color code

            idx = self.account_listbox.size() - 1

            if status == 'pending':

                self.account_listbox.itemconfig(idx, fg='#eab308')

            elif status == 'approved':

                self.account_listbox.itemconfig(idx, fg='#22c55e')

            elif status == 'rejected':

                self.account_listbox.itemconfig(idx, fg='#ef4444')

        self.pending_count_label.config(text=f'Chờ duyệt: {pending_count}')

        self.approved_count_label.config(text=f'Đã duyệt: {approved_count}')

        print(f"📋 Accounts loaded: {len(accounts)} (pending: {pending_count}, approved: {approved_count})")

    def _get_selected_account(self):

        """Lấy account đang được chọn trong listbox"""

        sel = self.account_listbox.curselection()

        if not sel:

            messagebox.showwarning("Chưa chọn", "Vui lòng chọn một tài khoản!")

            return None

        idx = sel[0]

        if idx < len(self._accounts_data):

            return self._accounts_data[idx]

        return None

    def approve_selected_account(self):

        """Duyệt tài khoản đang chọn"""

        acc = self._get_selected_account()

        if not acc:

            return

        if acc.get('status') == 'approved':

            messagebox.showinfo("Thông báo", f"Tài khoản '{acc['username']}' đã được duyệt rồi!")

            return

        if messagebox.askyesno("Duyệt tài khoản", f"Duyệt tài khoản '{acc['username']}'?"):

            accounts = self._load_accounts_local()

            for a in accounts:

                if a.get('id') == acc.get('id'):

                    a['status'] = 'approved'

                    a['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    break

            self._save_accounts_local(accounts)

            self.refresh_accounts()

            print(f"✅ Account approved: {acc['username']}")

            messagebox.showinfo("Thành công", f"✅ Đã duyệt tài khoản '{acc['username']}'")

    def reject_selected_account(self):

        """Từ chối tài khoản đang chọn"""

        acc = self._get_selected_account()

        if not acc:

            return

        if messagebox.askyesno("Từ chối tài khoản", f"Từ chối tài khoản '{acc['username']}'?"):

            accounts = self._load_accounts_local()

            for a in accounts:

                if a.get('id') == acc.get('id'):

                    a['status'] = 'rejected'

                    break

            self._save_accounts_local(accounts)

            self.refresh_accounts()

            print(f"❌ Account rejected: {acc['username']}")

    def delete_selected_account(self):

        """Xóa tài khoản đang chọn"""

        acc = self._get_selected_account()

        if not acc:

            return

        if messagebox.askyesno("Xóa tài khoản", 

                f"Xóa tài khoản '{acc['username']}'?\n\nHành động này không thể hoàn tác!"):

            accounts = self._load_accounts_local()

            accounts = [a for a in accounts if a.get('id') != acc.get('id')]

            self._save_accounts_local(accounts)

            self.refresh_accounts()

            print(f"🗑️ Account deleted: {acc['username']}")

            messagebox.showinfo("Đã xóa", f"🗑️ Đã xóa tài khoản '{acc['username']}'")

    def edit_selected_account(self):

        """Sửa tài khoản đang chọn — hiện dialog"""

        acc = self._get_selected_account()

        if not acc:

            return

        # Create edit dialog

        dialog = tk.Toplevel(self.root)

        dialog.title(f"Sửa tài khoản: {acc['username']}")

        dialog.geometry("400x380")

        dialog.configure(bg='#111827')

        dialog.resizable(False, False)

        dialog.grab_set()  # Modal

        C_CARD = '#1e293b'

        C_BG = '#0f1923'

        C_TEXT1 = '#e2e8f0'

        C_TEXT2 = '#94a3b8'

        C_BORDER = '#334155'

        C_BLUE = '#3b82f6'

        C_GREEN = '#22c55e'

        inner = tk.Frame(dialog, bg='#111827')

        inner.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        tk.Label(inner, text=f"Sửa tài khoản: {acc['username']}",

                 font=('Segoe UI', 14, 'bold'), bg='#111827', fg=C_TEXT1).pack(anchor='w', pady=(0, 16))

        # Fullname

        tk.Label(inner, text='Họ và tên:', font=('Segoe UI', 10),

                 bg='#111827', fg=C_TEXT2).pack(anchor='w', pady=(0, 4))

        fullname_var = tk.StringVar(value=acc.get('fullname', ''))

        tk.Entry(inner, textvariable=fullname_var, font=('Segoe UI', 11),

                 bg=C_BG, fg=C_TEXT1, insertbackground=C_TEXT1,

                 relief=tk.FLAT, bd=0, highlightbackground=C_BORDER,

                 highlightthickness=1).pack(fill=tk.X, ipady=6, pady=(0, 12))

        # New password (optional)

        tk.Label(inner, text='Mật khẩu mới (để trống = không đổi):',

                 font=('Segoe UI', 10), bg='#111827', fg=C_TEXT2).pack(anchor='w', pady=(0, 4))

        newpass_var = tk.StringVar()

        tk.Entry(inner, textvariable=newpass_var, font=('Segoe UI', 11), show='●',

                 bg=C_BG, fg=C_TEXT1, insertbackground=C_TEXT1,

                 relief=tk.FLAT, bd=0, highlightbackground=C_BORDER,

                 highlightthickness=1).pack(fill=tk.X, ipady=6, pady=(0, 12))

        # Status

        tk.Label(inner, text='Trạng thái:', font=('Segoe UI', 10),

                 bg='#111827', fg=C_TEXT2).pack(anchor='w', pady=(0, 4))

        status_var = tk.StringVar(value=acc.get('status', 'pending'))

        status_frame = tk.Frame(inner, bg='#111827')

        status_frame.pack(fill=tk.X, pady=(0, 12))

        for val, label in [('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Từ chối')]:

            tk.Radiobutton(status_frame, text=label, variable=status_var, value=val,

                          font=('Segoe UI', 10), bg='#111827', fg=C_TEXT1,

                          selectcolor=C_CARD, activebackground='#111827',

                          activeforeground=C_TEXT1).pack(side=tk.LEFT, padx=(0, 16))

        # Role

        tk.Label(inner, text='Vai trò:', font=('Segoe UI', 10),

                 bg='#111827', fg=C_TEXT2).pack(anchor='w', pady=(0, 4))

        role_var = tk.StringVar(value=acc.get('role', 'user'))

        role_frame = tk.Frame(inner, bg='#111827')

        role_frame.pack(fill=tk.X, pady=(0, 16))

        for val, label in [('user', 'Người dùng'), ('admin', 'Quản trị')]:

            tk.Radiobutton(role_frame, text=label, variable=role_var, value=val,

                          font=('Segoe UI', 10), bg='#111827', fg=C_TEXT1,

                          selectcolor=C_CARD, activebackground='#111827',

                          activeforeground=C_TEXT1).pack(side=tk.LEFT, padx=(0, 16))

        # Buttons

        btn_frame = tk.Frame(inner, bg='#111827')

        btn_frame.pack(fill=tk.X, pady=(8, 0))

        def save_changes():

            import hashlib as _hl

            accounts = self._load_accounts_local()

            for a in accounts:

                if a.get('id') == acc.get('id'):

                    a['fullname'] = fullname_var.get().strip()

                    a['status'] = status_var.get()

                    a['role'] = role_var.get()

                    new_pw = newpass_var.get()

                    if new_pw:

                        salt = 'solarpanel2025'

                        a['password_hash'] = _hl.sha256(f'{salt}:{new_pw}'.encode()).hexdigest()

                    if status_var.get() == 'approved' and not a.get('approved_at'):

                        a['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                    break

            self._save_accounts_local(accounts)

            self.refresh_accounts()

            dialog.destroy()

            messagebox.showinfo("Thành công", f"✅ Đã cập nhật tài khoản '{acc['username']}'")

        tk.Button(btn_frame, text='✖ Hủy', command=dialog.destroy,

                  font=('Segoe UI', 10, 'bold'), bg='#64748b', fg='white',

                  relief=tk.FLAT, bd=0, cursor='hand2', padx=20).pack(side=tk.LEFT, padx=(0, 8), ipady=4)

        tk.Button(btn_frame, text='✔ Lưu', command=save_changes,

                  font=('Segoe UI', 10, 'bold'), bg=C_GREEN, fg='white',

                  relief=tk.FLAT, bd=0, cursor='hand2', padx=20).pack(side=tk.LEFT, ipady=4)

    def start_web_server(self):

        """Khởi động web server - FastAPI + uvicorn (tự động khi login)"""

        if self.web_server_running:

            return

        try:

            import web_monitor_fastapi

            self.web_module = web_monitor_fastapi

            web_monitor_fastapi.APP_CONFIG_REF = CONFIG

            if not hasattr(web_monitor_fastapi, 'app') or web_monitor_fastapi.app is None:

                print("⚠️ FastAPI chưa được cài đặt!")

                return

            web_monitor_fastapi.app_instance = self

            web_monitor_fastapi.detector = self.detector

            web_monitor_fastapi.camera = self.camera

            web_monitor_fastapi.is_running = True

            capture_thread = threading.Thread(target=web_monitor_fastapi.capture_frames, daemon=True)

            capture_thread.start()

            self.web_server_running = True

            def run_server():

                try:

                    web_monitor_fastapi.run_server_thread(host='0.0.0.0', port=5000)

                except Exception as e:

                    print(f"FastAPI server error: {e}")

                    self.web_server_running = False

            self.web_server_thread = threading.Thread(target=run_server, daemon=True)

            self.web_server_thread.start()

            print("✅ Web server started: http://localhost:5000")

        except ImportError as e:

            print(f"⚠️ Không thể import web_monitor_fastapi: {e}")

        except Exception as e:

            print(f"⚠️ Không thể khởi động server: {e}")

    # ==================== ☁️ CLOUD API INTEGRATION ====================

    def _init_cloud_client(self):
        """Khởi tạo Cloud API Client nếu được bật."""
        if not CONFIG.get('CLOUD_ENABLED', False):
            print("☁️  Cloud sync: DISABLED (set CLOUD_ENABLED=True to enable)")
            if hasattr(self, 'cloud_status_label'):
                self.cloud_status_label.config(text="Đã tắt đồng bộ Cloud", fg=self._colors['text3'])
            return

        try:
            from cloud_api_client import CloudAPIClient

            self.cloud_client = CloudAPIClient(
                cloud_url=CONFIG['CLOUD_URL'],
                api_key=CONFIG['CLOUD_API_KEY'],
                device_id=CONFIG.get('CLOUD_DEVICE_ID', 'device-001'),
            )
            self.cloud_client.set_command_callback(self._handle_cloud_command)
            self.cloud_client.start()

            # Start background push thread
            self._cloud_push_thread = threading.Thread(
                target=self._cloud_push_loop, daemon=True, name='CloudPush'
            )
            self._cloud_push_thread.start()
            print("☁️  Cloud push thread started")

            if hasattr(self, 'cloud_status_label'):
                if self.cloud_client.is_connected:
                    self.cloud_status_label.config(text="ĐÃ KẾT NỐI", fg=self._colors['green'])
                else:
                    self.cloud_status_label.config(text="MẤT KẾT NỐI (Sẽ tự thử lại)", fg=self._colors['red'])

        except ImportError:
            print("⚠️ cloud_api_client.py không tìm thấy — Cloud sync disabled")
            if hasattr(self, 'cloud_status_label'):
                self.cloud_status_label.config(text="Lỗi: Không tìm thấy file client", fg=self._colors['red'])
        except Exception as e:
            print(f"⚠️ Cloud init error: {e}")
            if hasattr(self, 'cloud_status_label'):
                self.cloud_status_label.config(text=f"Lỗi: {e}", fg=self._colors['red'])

    def _build_cloud_status(self):
        """Xây dựng dict status giống current_results trong web_monitor."""
        try:
            label_name = getattr(self, '_last_label_name', 'Unknown')
            confidence = getattr(self, '_last_confidence', 0.0)
            area_ratio = getattr(self, '_last_area_ratio', 0.0)
            pred_probs = list(getattr(self, '_last_pred_probs', [0.0, 0.0]))
            pred_class = getattr(self, '_last_pred_class', 0)
            dirty_patch_count = getattr(self, '_last_dirty_patch_count', 0)
            valid_patch_count = getattr(self, '_last_valid_patch_count', 0)
            nopanel_patch_count = getattr(self, '_last_nopanel_patch_count', 0)
            cnn_active = bool(getattr(self, '_last_cnn_active', False))
            panel_detected = bool(getattr(self, '_last_panel_detected', False))
            yolo_clean_faults = list(getattr(self, '_last_yolo_clean_faults', []))
            yolo_crack_faults = list(getattr(self, '_last_yolo_crack_faults', []))
            clean_count = getattr(self, 'cleaning_count', 0)
            plc_connected = self.plc.is_connected if self.plc else False
            plc_ip = CONFIG['PLC'].get('IP', '192.168.0.1')

            # Status text
            is_running = getattr(self, 'is_running', False)
            if not is_running:
                status_text = 'Đang dừng — Nhấn START để bắt đầu'
                status_color = 'warning'
            elif label_name.lower() in ('ban', 'dirty'):
                status_text = f'⚠️ PHÁT HIỆN BẨN — {label_name} ({confidence*100:.1f}%)'
                status_color = 'danger'
            else:
                status_text = f'✅ SẠCH — {label_name} ({confidence*100:.1f}%)'
                status_color = 'success'

            # FPS
            elapsed = time.time() - self.start_time if self.start_time else 1
            fps = self.total_frames / elapsed if elapsed > 0 else 0

            # Next snapshot countdown
            next_snapshot = 0
            snapshot_ts = getattr(self, '_last_snapshot_timestamp', None)
            if snapshot_ts:
                elapsed_since = time.time() - snapshot_ts
                interval = CONFIG.get('SNAPSHOT_INTERVAL', 600)
                next_snapshot = max(0, int(interval - elapsed_since))

            data = {
                'label_name': label_name,
                'confidence': float(confidence),
                'area_ratio': float(area_ratio),
                'pred_probs': pred_probs,
                'predicted_class': int(pred_class),
                'dirty_patch_count': int(dirty_patch_count),
                'valid_patch_count': int(valid_patch_count),
                'nopanel_patch_count': int(nopanel_patch_count),
                'cnn_active': cnn_active,
                'panel_detected': panel_detected,
                'yolo_clean_faults': yolo_clean_faults,
                'yolo_crack_faults': yolo_crack_faults,
                'status': status_text,
                'status_color': status_color,
                'fps': round(fps, 1),
                'clean_count': clean_count,
                'plc_connected': plc_connected,
                'plc_ip': plc_ip,
                'is_running': is_running,
                'snapshot_interval': CONFIG.get('SNAPSHOT_INTERVAL', 600),
                'dirt_threshold': CONFIG.get('DIRT_AREA_THRESHOLD', 0.06),
                'cnn_dirty_threshold': CONFIG.get('CNN_DIRTY_THRESHOLD', 0.05),
                'camera_id': CONFIG.get('CAMERA_ID', 0),
                'next_snapshot': next_snapshot,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # Snapshot info
            snapshot_path = getattr(self, '_last_snapshot_filename', None)
            if snapshot_path:
                data['last_snapshot_path'] = snapshot_path
            snapshot_time = getattr(self, '_last_snapshot_time', None)
            if snapshot_time:
                data['last_snapshot_time'] = snapshot_time

            # Power data
            if self.power_monitor:
                pm = self.power_monitor
                data['power_voltage'] = pm.current.get('voltage', 0)
                data['power_current'] = pm.current.get('current', 0)
                data['power_watts'] = pm.current.get('power', 0)
                data['power_energy'] = pm.current.get('energy', 0)

            if self.efficiency_tracker:
                if self.efficiency_tracker._pending_event:
                    data['last_efficiency'] = {
                        'status': 'measuring',
                        'pre_power': self.efficiency_tracker._pending_event.get('pre_clean_power', 0),
                        'post_power': 0.0,
                        'improvement_pct': 0.0,
                    }
                else:
                    ev = self.efficiency_tracker.get_last_event()
                    if ev:
                        data['last_efficiency'] = {
                            'status': 'done',
                            'pre_power': ev.get('pre_clean_power', 0),
                            'post_power': ev.get('post_clean_power', 0),
                            'improvement_pct': ev.get('improvement_pct', 0),
                        }

            return data
        except Exception as e:
            return {'status': f'Error: {e}', 'status_color': 'danger'}

    def _cloud_push_loop(self):
        """Background thread: push data lên cloud định kỳ."""
        status_interval = CONFIG.get('CLOUD_PUSH_INTERVAL', 2)
        frame_interval = CONFIG.get('CLOUD_FRAME_INTERVAL', 3)
        last_status_push = 0
        last_frame_push = 0
        last_power_push = 0

        client_ref = self.cloud_client
        while client_ref and client_ref._running:
            try:
                now = time.time()

                # Cập nhật kết nối lên giao diện định kỳ
                if hasattr(self, 'cloud_status_label') and hasattr(self, '_colors'):
                    if client_ref.is_connected:
                        self.root.after(0, lambda: self.cloud_status_label.config(text="ĐÃ KẾT NỐI", fg=self._colors['green']))
                    else:
                        self.root.after(0, lambda: self.cloud_status_label.config(text="MẤT KẾT NỐI (Sẽ tự thử lại)", fg=self._colors['red']))

                # Push AI status
                if now - last_status_push >= status_interval:
                    status = self._build_cloud_status()
                    client_ref.push_status(status)
                    last_status_push = now

                # Push camera frame
                if now - last_frame_push >= frame_interval:
                    frame = getattr(self, '_last_frame', None)
                    if frame is not None:
                        try:
                            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                            client_ref.push_frame(jpeg.tobytes(), 'main')
                        except Exception:
                            pass

                    # Push CNN patch frame
                    cnn_frame = getattr(self, '_last_cnn_patch_frame', None)
                    if cnn_frame is not None:
                        try:
                            _, jpeg = cv2.imencode('.jpg', cnn_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                            client_ref.push_frame(jpeg.tobytes(), 'cnn_patch')
                        except Exception:
                            pass

                    # Push YOLO panel frame
                    yolo_frame = getattr(self, '_last_yolo_panel_frame', None)
                    if yolo_frame is not None:
                        try:
                            _, jpeg = cv2.imencode('.jpg', yolo_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                            client_ref.push_frame(jpeg.tobytes(), 'yolo_panel')
                        except Exception:
                            pass

                    last_frame_push = now

                # Push power data (mỗi 10s)
                if now - last_power_push >= 10 and self.power_monitor:
                    try:
                        pm = self.power_monitor.current
                        if pm.get('power', 0) > 0 or pm.get('voltage', 0) > 0:
                            client_ref.push_power({
                                'voltage': pm.get('voltage', 0),
                                'current': pm.get('current', 0),
                                'power': pm.get('power', 0),
                                'energy': pm.get('energy', 0),
                            })
                    except Exception:
                        pass
                    last_power_push = now

            except Exception as e:
                print(f"☁️  Push error: {e}")

            time.sleep(0.5)

    def _handle_cloud_command(self, command, value):
        """Xử lý lệnh từ Cloud (giống Web commands)."""
        print(f"☁️  📥 Cloud command: {command} = {value}")

        # Dùng root.after() để chạy trong main thread (thread-safe cho Tkinter)
        if command == 'camera':
            self.root.after(0, lambda: self._apply_cloud_cmd('camera', value))
        elif command == 'threshold':
            self.root.after(0, lambda: self._apply_cloud_cmd('threshold', value))
        elif command == 'cnn_dirty_threshold':
            self.root.after(0, lambda: self._apply_cloud_cmd('cnn_dirty_threshold', value))
        elif command == 'snapshot_interval':
            self.root.after(0, lambda: self._apply_cloud_cmd('snapshot_interval', value))
        elif command == 'plc_ip_update':
            self.root.after(0, lambda: self._apply_cloud_cmd('plc_ip_update', value))
        elif command == 'manual_clean':
            self.root.after(0, lambda: self._apply_cloud_cmd('manual_clean', value))
        elif command == 'system_start':
            self.root.after(0, lambda: self._apply_cloud_cmd('system_start', value))
        elif command == 'system_stop':
            self.root.after(0, lambda: self._apply_cloud_cmd('system_stop', value))
        elif command == 'plc_reconnect':
            self.root.after(0, lambda: self._apply_cloud_cmd('plc_reconnect', value))
        elif command == 'min_confidence':
            CONFIG['MIN_CONFIDENCE'] = float(value)
            print(f"✅ MIN_CONFIDENCE updated from Cloud: {value}")
        else:
            print(f"⚠️ Unknown cloud command: {command}")

    def _apply_cloud_cmd(self, cmd, value):
        """Apply cloud command trong main thread (qua web_module queue nếu có)."""
        if self.web_module and hasattr(self.web_module, 'command_queue'):
            # Reuse existing queue → process_web_commands() sẽ xử lý
            self.web_module.command_queue.put((cmd, value))
        else:
            # Fallback: xử lý trực tiếp
            if cmd == 'system_start' and not self.is_running:
                self.start_monitoring()
            elif cmd == 'system_stop' and self.is_running:
                self.stop_monitoring()
            elif cmd == 'manual_clean' and self.plc and self.plc.is_connected:
                success = self.plc.trigger_cleaning()
                if success:
                    self.cleaning_count += 1
                    if self.efficiency_tracker:
                        self.efficiency_tracker.on_cleaning_started(
                            trigger_reason='Manual Clean (Cloud)',
                            dirty_ratio=0.0,
                            ai_label='Manual',
                            ai_confidence=1.0,
                        )
            elif cmd == 'threshold':
                CONFIG['DIRT_AREA_THRESHOLD'] = float(value)
            elif cmd == 'cnn_dirty_threshold':
                CONFIG['CNN_DIRTY_THRESHOLD'] = float(value)
            elif cmd == 'snapshot_interval':
                CONFIG['SNAPSHOT_INTERVAL'] = int(value)
            elif cmd == 'plc_ip_update':
                CONFIG['PLC']['IP'] = str(value).strip()


    def stop_web_server(self):

        """Dừng web server"""

        if not self.web_server_running:

            return

        try:

            if self.web_module:

                self.web_module.is_running = False

            self.web_server_running = False

            print("✅ Web server stopped.")

        except Exception as e:

            print(f"Stop server error: {e}")

    def open_browser(self):

        """Mở browser"""

        import webbrowser

        webbrowser.open('http://localhost:5000')

    def on_closing(self):

        """Xử lý đóng app"""

        if messagebox.askokcancel("Thoát", "Thoát ứng dụng?"):

            self.is_running = False

            self.camera_preview_running = False

            self.web_server_running = False

            # ☁️ Stop cloud client

            if self.cloud_client:

                self.cloud_client.stop()

            if self.power_monitor:

                self.power_monitor.stop()

            if self.camera:

                self.camera.release()

            if self.plc:

                self.plc.disconnect()

            self.root.destroy()

# ==================== POWER ANALYSIS WINDOW ====================

class PowerAnalysisWindow(tk.Toplevel):
    """⚡ Cửa sổ phân tích công suất DC (PZEM-017) — trang riêng biệt."""

    def __init__(self, parent, power_monitor, efficiency_tracker):
        super().__init__(parent)
        self.pm = power_monitor
        self.et = efficiency_tracker
        self._running = True
        self._chart_mode = 'Real-time'
        self._last_db_plot_time = 0

        # Window setup
        self.title('⚡ Power Analysis — PZEM-017 DC Monitor')
        self.geometry('1100x720')
        self.configure(bg='#0f1923')
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        # Colors
        C = {
            'bg': '#0f1923', 'panel': '#172030', 'card': '#1e293b',
            'header': '#111827', 'border': '#334155',
            'text1': '#e2e8f0', 'text2': '#94a3b8', 'text3': '#64748b',
            'green': '#22c55e', 'red': '#ef4444', 'blue': '#3b82f6',
            'yellow': '#f59e0b', 'cyan': '#06b6d4',
        }
        self._C = C

        # ── Header ──
        hdr = tk.Frame(self, bg=C['header'], height=48)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text='⚡ POWER ANALYSIS — PZEM-017 DC',
                 font=('Segoe UI', 14, 'bold'), bg=C['header'], fg=C['yellow']
                 ).pack(side=tk.LEFT, padx=16)
        tk.Label(hdr, text='Real-time Solar Panel Power Monitoring',
                 font=('Segoe UI', 10), bg=C['header'], fg=C['text3']
                 ).pack(side=tk.LEFT, padx=8)

        # ── KPI Strip ──
        kpi_frame = tk.Frame(self, bg=C['bg'])
        kpi_frame.pack(fill=tk.X, padx=12, pady=(12, 0))

        self.kpi_labels = {}
        kpi_defs = [
            ('voltage', 'Điện áp (V)', C['cyan'], '0.00 V'),
            ('current', 'Dòng điện (A)', C['green'], '0.000 A'),
            ('power', 'Công suất (W)', C['yellow'], '0.0 W'),
            ('energy', 'Năng lượng (kWh)', C['blue'], '0.000 kWh'),
        ]

        for key, label, color, default_val in kpi_defs:
            card = tk.Frame(kpi_frame, bg=C['card'],
                           highlightbackground=C['border'], highlightthickness=1)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
            tk.Label(card, text=label, font=('Segoe UI', 9, 'bold'),
                     bg=C['card'], fg=C['text3']).pack(anchor='w', padx=12, pady=(10, 0))
            val_lbl = tk.Label(card, text=default_val,
                              font=('Consolas', 22, 'bold'), bg=C['card'], fg=color)
            val_lbl.pack(anchor='w', padx=12, pady=(2, 10))
            self.kpi_labels[key] = val_lbl

        # ── Main content ──
        content = tk.Frame(self, bg=C['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Left: Charts
        left = tk.Frame(content, bg=C['bg'])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        # Power chart (matplotlib)
        self._has_matplotlib = False
        try:
            import matplotlib
            matplotlib.use('Agg')
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            chart_card = tk.Frame(left, bg=C['card'],
                                 highlightbackground=C['border'], highlightthickness=1)
            chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
            
            # Header frame với bộ chuyển chế độ biểu đồ và nút xuất ảnh/dữ liệu
            chart_hdr = tk.Frame(chart_card, bg=C['header'])
            chart_hdr.pack(fill=tk.X)
            
            self.chart_title_lbl = tk.Label(chart_hdr, text='  📈 CÔNG SUẤT DC REAL-TIME',
                                            font=('Segoe UI', 10, 'bold'), bg=C['header'], fg=C['text3'],
                                            anchor='w')
            self.chart_title_lbl.pack(side=tk.LEFT, ipady=5)
            
            ctrl_container = tk.Frame(chart_hdr, bg=C['header'])
            ctrl_container.pack(side=tk.RIGHT, padx=5)
            
            self.mode_var = tk.StringVar(value='Real-time')
            self.mode_combo = ttk.Combobox(ctrl_container, textvariable=self.mode_var,
                                           values=['Real-time', 'Theo Giờ', 'Theo Ngày', 'Theo Tháng'],
                                           state='readonly', width=12)
            self.mode_combo.pack(side=tk.LEFT, padx=5)
            self.mode_combo.bind('<<ComboboxSelected>>', self._on_chart_mode_changed)
            
            self.btn_export_png = tk.Button(ctrl_container, text='📸 Ảnh (PNG)',
                                            font=('Segoe UI', 8, 'bold'),
                                            bg=C['blue'], fg='#ffffff',
                                            activebackground=C['cyan'], activeforeground='#ffffff',
                                            relief=tk.FLAT, bd=0, padx=8, pady=2,
                                            command=self._export_chart_png)
            self.btn_export_png.pack(side=tk.LEFT, padx=2)
            
            self.btn_export_csv = tk.Button(ctrl_container, text='📥 Excel (CSV)',
                                            font=('Segoe UI', 8, 'bold'),
                                            bg=C['green'], fg='#ffffff',
                                            activebackground='#16a34a', activeforeground='#ffffff',
                                            relief=tk.FLAT, bd=0, padx=8, pady=2,
                                            command=self._export_data_csv)
            self.btn_export_csv.pack(side=tk.LEFT, padx=2)
            
            self.btn_export_json = tk.Button(ctrl_container, text='📦 JSON',
                                             font=('Segoe UI', 8, 'bold'),
                                             bg=C['yellow'], fg='#ffffff',
                                             activebackground='#d97706', activeforeground='#ffffff',
                                             relief=tk.FLAT, bd=0, padx=8, pady=2,
                                             command=self._export_data_json)
            self.btn_export_json.pack(side=tk.LEFT, padx=2)

            self.fig = Figure(figsize=(7, 2.8), facecolor='#1e293b')
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor('#0f1923')
            self.ax.tick_params(colors='#94a3b8', labelsize=8)
            for sp in ('bottom', 'left'):
                self.ax.spines[sp].set_color('#334155')
            for sp in ('top', 'right'):
                self.ax.spines[sp].set_visible(False)
            self.ax.set_ylabel('W', color='#94a3b8', fontsize=9)
            self.fig.tight_layout(pad=2)

            self.canvas_chart = FigureCanvasTkAgg(self.fig, master=chart_card)
            self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._has_matplotlib = True
        except ImportError:
            tk.Label(left, text='matplotlib chưa cài đặt\npip install matplotlib',
                     font=('Segoe UI', 11), bg=C['card'], fg=C['text3']
                     ).pack(fill=tk.BOTH, expand=True, pady=40)

        # Comparison section
        comp_card = tk.Frame(left, bg=C['card'],
                             highlightbackground=C['border'], highlightthickness=1)
        comp_card.pack(fill=tk.X)
        tk.Label(comp_card, text='  📊 SO SÁNH TRƯỚC / SAU VỆ SINH',
                 font=('Segoe UI', 10, 'bold'), bg=C['header'], fg=C['text3'],
                 anchor='w').pack(fill=tk.X, ipady=5)

        self.comp_frame = tk.Frame(comp_card, bg=C['card'])
        self.comp_frame.pack(fill=tk.X, padx=12, pady=10)
        self.comp_pre_label = tk.Label(self.comp_frame, text='Trước: -- W',
                                       font=('Consolas', 14, 'bold'), bg=C['card'], fg=C['red'])
        self.comp_pre_label.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(self.comp_frame, text='→',
                 font=('Segoe UI', 16, 'bold'), bg=C['card'], fg=C['text3']
                 ).pack(side=tk.LEFT, padx=10)
        self.comp_post_label = tk.Label(self.comp_frame, text='Sau: -- W',
                                        font=('Consolas', 14, 'bold'), bg=C['card'], fg=C['green'])
        self.comp_post_label.pack(side=tk.LEFT, padx=(20, 0))
        self.comp_delta_label = tk.Label(self.comp_frame, text='Chờ dữ liệu vệ sinh...',
                                         font=('Segoe UI', 12, 'bold'), bg=C['card'], fg=C['text3'])
        self.comp_delta_label.pack(side=tk.RIGHT)

        # Right: History table
        right = tk.Frame(content, bg=C['bg'], width=380)
        right.pack(side=tk.RIGHT, fill=tk.BOTH)
        right.pack_propagate(False)

        hist_card = tk.Frame(right, bg=C['card'],
                             highlightbackground=C['border'], highlightthickness=1)
        hist_card.pack(fill=tk.BOTH, expand=True)
        tk.Label(hist_card, text='  📋 LỊCH SỬ VỆ SINH',
                 font=('Segoe UI', 10, 'bold'), bg=C['header'], fg=C['text3'],
                 anchor='w').pack(fill=tk.X, ipady=5)

        # Treeview
        style = ttk.Style()
        style.configure('Power.Treeview', background='#1e293b', foreground='#e2e8f0',
                        fieldbackground='#1e293b', rowheight=28, font=('Consolas', 9))
        style.configure('Power.Treeview.Heading', background='#111827',
                        foreground='#94a3b8', font=('Segoe UI', 9, 'bold'))

        cols = ('time', 'reason', 'pre', 'post', 'gain', 'pct')
        self.tree = ttk.Treeview(hist_card, columns=cols, show='headings',
                                style='Power.Treeview', height=12)
        self.tree.heading('time', text='Thời gian')
        self.tree.heading('reason', text='Lý do')
        self.tree.heading('pre', text='P trước')
        self.tree.heading('post', text='P sau')
        self.tree.heading('gain', text='ΔP')
        self.tree.heading('pct', text='η%')
        self.tree.column('time', width=75, anchor='center')
        self.tree.column('reason', width=90)
        self.tree.column('pre', width=55, anchor='e')
        self.tree.column('post', width=55, anchor='e')
        self.tree.column('gain', width=50, anchor='e')
        self.tree.column('pct', width=50, anchor='e')

        scroll = ttk.Scrollbar(hist_card, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0), pady=4)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # Load history + start update loop
        self._load_history()
        self._update()

    def _on_close(self):
        self._running = False
        self.destroy()

    def _update(self):
        """Cập nhật KPI + biểu đồ mỗi 2 giây."""
        if not self._running or not self.winfo_exists():
            return

        try:
            # KPI
            if self.pm and self.pm.current:
                d = self.pm.current
                self.kpi_labels['voltage'].config(text=f"{d.get('voltage', 0):.2f} V")
                self.kpi_labels['current'].config(text=f"{d.get('current', 0):.3f} A")
                self.kpi_labels['power'].config(text=f"{d.get('power', 0):.1f} W")
                self.kpi_labels['energy'].config(text=f"{d.get('energy', 0):.3f} kWh")

            # Comparison
            if self.et:
                if self.et._pending_event:
                    self.comp_delta_label.config(text="Đang đo hiệu suất...", fg=self._C['yellow'])
                else:
                    ev = self.et.get_last_event()
                    if ev:
                        pre = ev.get('pre_clean_power', 0)
                        post = ev.get('post_clean_power', 0)
                        gain = ev.get('power_gain', 0)
                        pct = ev.get('improvement_pct', 0)
                        self.comp_pre_label.config(text=f"Trước: {pre:.1f} W")
                        self.comp_post_label.config(text=f"Sau: {post:.1f} W")
                        color = self._C['green'] if gain >= 0 else self._C['red']
                        self.comp_delta_label.config(
                            text=f"ΔP = {gain:+.1f}W  |  η = {pct:+.1f}%", fg=color)
                        self._load_history()

            # Chart
            if self._has_matplotlib:
                now = time.time()
                is_db_mode = self._chart_mode != 'Real-time'
                should_draw = not is_db_mode or (now - self._last_db_plot_time >= 30)

                if should_draw:
                    self._draw_chart()

        except Exception as e:
            print(f"PowerWindow update error: {e}")

        self.after(2000, self._update)

    def _draw_chart(self):
        """Vẽ lại biểu đồ dựa trên chế độ hiện tại."""
        if not self._has_matplotlib:
            return
        try:
            is_db_mode = self._chart_mode != 'Real-time'
            if not is_db_mode:
                if self.pm:
                    hist = list(self.pm.history)
                    if hist:
                        times = [h.get('timestamp', '')[-8:] for h in hist]
                        powers = [h.get('power', 0) for h in hist]

                        self.ax.clear()
                        self.ax.set_facecolor('#0f1923')
                        self.ax.fill_between(range(len(powers)), powers,
                                             alpha=0.2, color='#f59e0b')
                        self.ax.plot(powers, color='#f59e0b', linewidth=1.5)
                        self.ax.set_ylabel('Công suất (W)', color='#94a3b8', fontsize=9)
                        self.ax.tick_params(colors='#94a3b8', labelsize=7)
                        for sp in ('bottom', 'left'):
                            self.ax.spines[sp].set_color('#334155')
                        for sp in ('top', 'right'):
                            self.ax.spines[sp].set_visible(False)

                        n = len(times)
                        if n > 6:
                            step = n // 6
                            ticks = list(range(0, n, step))
                            self.ax.set_xticks(ticks)
                            self.ax.set_xticklabels([times[i] for i in ticks], fontsize=7)

                        self.fig.tight_layout(pad=2)
                        self.canvas_chart.draw_idle()
            else:
                self.ax.clear()
                self.ax.set_facecolor('#0f1923')
                for sp in ('bottom', 'left'):
                    self.ax.spines[sp].set_color('#334155')
                for sp in ('top', 'right'):
                    self.ax.spines[sp].set_visible(False)
                self.ax.tick_params(colors='#94a3b8', labelsize=7)

                data_found = False

                if self._chart_mode == 'Theo Giờ':
                    from power_db import get_hourly_stats
                    rows = get_hourly_stats()
                    if rows:
                        data_found = True
                        hours = [r['hour'] + 'h' for r in rows]
                        avg_powers = [r['avg_power'] for r in rows]
                        x_idx = range(len(hours))
                        self.ax.plot(x_idx, avg_powers, color='#06b6d4', linewidth=1.5, marker='o', markersize=3)
                        self.ax.fill_between(x_idx, avg_powers, color='#06b6d4', alpha=0.15)
                        self.ax.set_ylabel('Công suất TB (W)', color='#94a3b8', fontsize=9)
                        self.ax.set_xticks(x_idx)
                        self.ax.set_xticklabels(hours, fontsize=7)
                        for i, val in enumerate(avg_powers):
                            self.ax.annotate(f'{val:.0f}',
                                            xy=(i, val),
                                            xytext=(0, 3),
                                            textcoords="offset points",
                                            ha='center', va='bottom', color='#e2e8f0', fontsize=6)

                elif self._chart_mode == 'Theo Ngày':
                    from power_db import get_daily_stats
                    rows = get_daily_stats(days=30)
                    if rows:
                        data_found = True
                        dates = [r['date'][-5:] for r in rows]
                        energies = [r['total_energy'] for r in rows]
                        x_idx = range(len(dates))
                        self.ax.plot(x_idx, energies, color='#3b82f6', linewidth=1.5, marker='o', markersize=3)
                        self.ax.fill_between(x_idx, energies, color='#3b82f6', alpha=0.15)
                        self.ax.set_ylabel('Sản lượng (kWh)', color='#94a3b8', fontsize=9)
                        self.ax.tick_params(axis='x', rotation=45)
                        self.ax.set_xticks(x_idx)
                        self.ax.set_xticklabels(dates, fontsize=7)
                        for i, val in enumerate(energies):
                            if len(energies) > 15 and i % 3 != 0:
                                continue
                            self.ax.annotate(f'{val:.2f}',
                                            xy=(i, val),
                                            xytext=(0, 3),
                                            textcoords="offset points",
                                            ha='center', va='bottom', color='#e2e8f0', fontsize=6)

                elif self._chart_mode == 'Theo Tháng':
                    from power_db import get_monthly_stats
                    rows = get_monthly_stats()
                    if rows:
                        data_found = True
                        months = ['Th.' + r['month'] for r in rows]
                        energies = [r['total_energy'] for r in rows]
                        x_idx = range(len(months))
                        self.ax.plot(x_idx, energies, color='#22c55e', linewidth=1.5, marker='o', markersize=3)
                        self.ax.fill_between(x_idx, energies, color='#22c55e', alpha=0.15)
                        self.ax.set_ylabel('Sản lượng (kWh)', color='#94a3b8', fontsize=9)
                        self.ax.set_xticks(x_idx)
                        self.ax.set_xticklabels(months, fontsize=7)
                        for i, val in enumerate(energies):
                            self.ax.annotate(f'{val:.1f}',
                                            xy=(i, val),
                                            xytext=(0, 3),
                                            textcoords="offset points",
                                            ha='center', va='bottom', color='#e2e8f0', fontsize=6)

                if not data_found:
                    self.ax.text(0.5, 0.5, 'Chưa có dữ liệu lịch sử',
                                 horizontalalignment='center', verticalalignment='center',
                                 transform=self.ax.transAxes, color='#94a3b8', fontsize=10)

                self.fig.tight_layout(pad=2)
                self.canvas_chart.draw_idle()
                self._last_db_plot_time = time.time()
        except Exception as e:
            print(f"Chart redraw error: {e}")

    def _on_chart_mode_changed(self, event=None):
        self._chart_mode = self.mode_var.get()
        self._last_db_plot_time = 0
        modes = {
            'Real-time': '  📈 CÔNG SUẤT DC REAL-TIME',
            'Theo Giờ': '  📈 CÔNG SUẤT TRUNG BÌNH THEO GIỜ',
            'Theo Ngày': '  📊 SẢN LƯỢNG ĐIỆN HÀNG NGÀY (kWh)',
            'Theo Tháng': '  📊 SẢN LƯỢNG ĐIỆN HÀNG THÁNG (kWh)'
        }
        self.chart_title_lbl.config(text=modes.get(self._chart_mode, '  📈 CÔNG SUẤT DC'))
        self._draw_chart()

    def _export_chart_png(self):
        """Lưu hình ảnh biểu đồ hiện tại thành file PNG."""
        if not self._has_matplotlib:
            messagebox.showerror('Lỗi', 'Không thể xuất biểu đồ vì matplotlib chưa cài đặt!')
            return
        
        from tkinter import filedialog
        mode_slug = self._chart_mode.replace(' ', '_').lower()
        default_filename = f"bieu_do_pzem_{mode_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title='Lưu hình ảnh biểu đồ',
            initialfile=default_filename,
            filetypes=[('PNG Image', '*.png'), ('All Files', '*.*')]
        )
        if not filepath:
            return
        
        try:
            self.fig.savefig(filepath, dpi=150, facecolor=self.fig.get_facecolor(), edgecolor='none')
            messagebox.showinfo('Thành công', f'Đã lưu ảnh biểu đồ tại:\n{filepath}')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Không thể lưu hình ảnh biểu đồ: {e}')

    def _export_data_csv(self):
        """Xuất toàn bộ dữ liệu đo đạc lịch sử ra file CSV."""
        from tkinter import filedialog
        default_filename = f"lich_su_cong_suat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title='Xuất dữ liệu lịch sử (CSV)',
            initialfile=default_filename,
            filetypes=[('CSV File', '*.csv'), ('All Files', '*.*')]
        )
        if not filepath:
            return
        
        try:
            from power_db import export_readings_to_csv
            success = export_readings_to_csv(filepath)
            if success:
                messagebox.showinfo('Thành công', f'Đã xuất dữ liệu lịch sử thành công tại:\n{filepath}')
            else:
                messagebox.showerror('Lỗi', 'Không thể xuất dữ liệu lịch sử (lỗi ghi file).')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Lỗi khi xuất dữ liệu: {e}')

    def _export_data_json(self):
        """Xuất toàn bộ dữ liệu đo đạc lịch sử ra file JSON."""
        from tkinter import filedialog
        default_filename = f"lich_su_cong_suat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title='Xuất dữ liệu lịch sử (JSON)',
            initialfile=default_filename,
            filetypes=[('JSON File', '*.json'), ('All Files', '*.*')]
        )
        if not filepath:
            return
        
        try:
            from power_db import export_readings_to_json
            success = export_readings_to_json(filepath)
            if success:
                messagebox.showinfo('Thành công', f'Đã xuất dữ liệu lịch sử thành công tại:\n{filepath}')
            else:
                messagebox.showerror('Lỗi', 'Không thể xuất dữ liệu lịch sử (lỗi ghi file).')
        except Exception as e:
            messagebox.showerror('Lỗi', f'Lỗi khi xuất dữ liệu: {e}')

    def _load_history(self):
        """Tải lịch sử vệ sinh từ SQLite."""
        try:
            from power_db import get_cleaning_events
            events = get_cleaning_events(limit=50)
            for item in self.tree.get_children():
                self.tree.delete(item)
            for ev in events:
                t = ev.get('start_time', '')[-8:] if ev.get('start_time') else ''
                self.tree.insert('', 'end', values=(
                    t,
                    ev.get('trigger_reason', '')[:15],
                    f"{ev.get('pre_clean_power', 0):.0f}",
                    f"{ev.get('post_clean_power', 0):.0f}",
                    f"{ev.get('power_gain', 0):+.0f}",
                    f"{ev.get('improvement_pct', 0):+.1f}",
                ))
        except Exception as e:
            print(f"Load cleaning history error: {e}")


def main():

    print("="*60)

    print("\U0001f31e SOLAR PANEL AUTO-CLEANING SYSTEM - TFLite Edition")

    print("="*60)

    print(f"Version: {CONFIG['APP_VERSION']}")

    print(f"Model: {CONFIG['MODEL_PATH']}")

    print(f"Runtime: {'tflite-runtime' if TFLITE_RUNTIME else 'tensorflow.lite'}")

    print(f"Auto-trigger class: '{CONFIG['TRIGGER_CLASS']}'")

    print(f"PLC IP: {CONFIG['PLC']['IP']}")

    print(f"PLC DB: DB{CONFIG['PLC']['DB_NUMBER']}.DBX{CONFIG['PLC']['DB_START']}.0")

    print("="*60)

    # Cùng 1 cửa sổ: Login → App

    root = tk.Tk()

    root.title('Solar Panel Cleaning — Login')

    root.state('zoomed')

    root.configure(bg='#0b0e14')

    app_instance_holder = {}

    def launch_app():
        """Đăng nhập thành công → build giao diện app trong cùng window"""
        try:
            app = SolarPanelCleaningApp(root)
            app_instance_holder['app'] = app
            root.protocol("WM_DELETE_WINDOW", app.on_closing)
        except Exception as e:
            print(f"❌ LỖI KHỞI ĐỘNG ỨNG DỤNG: {e}")
            import traceback
            traceback.print_exc()

    # Chặn đóng khi chưa login
    root.protocol("WM_DELETE_WINDOW", root.destroy)

    # Hiện login overlay → khi thành công gọi launch_app()
    LoginWindow(root, on_success=launch_app)


    root.mainloop()


if __name__ == "__main__":

    main()
