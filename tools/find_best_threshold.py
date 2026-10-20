import os
import argparse
import numpy as np

# Set TensorFlow log levels
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

try:
    import tensorflow as tf
    from tensorflow.keras import layers
    from tensorflow.keras.applications import EfficientNetB0
except ImportError:
    print("Error: TensorFlow is not installed. Please run this script within the project environment.")
    exit(1)

# Helper function to compute F1 Score (fallback in case scikit-learn is not installed)
def compute_f1(y_true, y_pred):
    try:
        from sklearn.metrics import f1_score
        return f1_score(y_true, y_pred, zero_division=0)
    except ImportError:
        # Custom numpy implementation
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        if tp == 0:
            return 0.0
        precision = tp / (tp + fp)
        recall = tp / (tp + fn)
        if precision + recall == 0:
            return 0.0
        return 2 * (precision * recall) / (precision + recall)

def find_best_threshold(model_path, val_dir, patch_size=224):
    if not os.path.exists(model_path):
        print(f"Error: Model path '{model_path}' does not exist.")
        return
        
    if not os.path.exists(val_dir):
        print(f"Error: Validation directory '{val_dir}' does not exist.")
        return

    # Check for subdirectories 'sach' (clean, 0) and 'ban' (dirty, 1)
    class_names = ['sach', 'ban']
    for cls in class_names:
        cls_dir = os.path.join(val_dir, cls)
        if not os.path.exists(cls_dir):
            print(f"Warning: Expected subdirectory '{cls}' not found in '{val_dir}'. Trying to load all files...")

    print(f"Loading dataset from '{val_dir}'...")
    try:
        val_ds = tf.keras.utils.image_dataset_from_directory(
            val_dir,
            labels='inferred',
            label_mode='int',
            class_names=class_names,
            batch_size=32,
            image_size=(patch_size, patch_size),
            shuffle=False
        )
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return

    print("Recreating EfficientNetB0 network architecture...")
    data_augmentation = tf.keras.Sequential([
        layers.RandomFlip("horizontal_and_vertical"),
        layers.RandomRotation(0.2),
    ], name="sequential")
    base_model = EfficientNetB0(input_shape=(patch_size, patch_size, 3), 
                                include_top=False, 
                                weights=None)
    base_model._name = "functional"
    inputs = tf.keras.Input(shape=(patch_size, patch_size, 3))
    x = data_augmentation(inputs)
    x = base_model(x, training=False)
    x = layers.GlobalAveragePooling2D(name="global_average_pooling2d")(x)
    x = layers.Dropout(0.2, name="dropout")(x)
    outputs = layers.Dense(2, activation='softmax', name="dense")(x)
    model = tf.keras.Model(inputs, outputs)
    
    print("Loading model weights...")
    try:
        model.load_weights(model_path)
        print("CNN model successfully loaded (CPU mode).")
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
                    model.get_layer('dense').set_weights(dense_w)
                    
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
            print("[OK] Đã ánh xạ thành công các trọng số Keras 3 sang cấu trúc model Keras 2.")
        except Exception as map_err:
            print(f"[ERROR] Thất bại khi ánh xạ trọng số thủ công: {map_err}")
            exit(1)

    probs = []
    labels = []
    
    print("Running batch inference on validation set...")
    for imgs, targets in val_ds:
        # EfficientNetB0 expects 0-255 RGB float32, which is the default output format of image_dataset_from_directory
        outputs = model.predict(imgs, verbose=0)
        # Class 1 is 'ban' (dirty)
        prob = outputs[:, 1]
        probs.extend(prob)
        labels.extend(targets.numpy())

    probs = np.array(probs)
    labels = np.array(labels)

    if len(probs) == 0:
        print("Error: No validation images were processed.")
        return

    print(f"Processed {len(probs)} validation images.")
    print("Searching for the optimal threshold (0.3 to 0.8 with 0.01 steps)...")
    
    thresholds = np.arange(0.3, 0.8, 0.01)
    f1_scores = [compute_f1(labels, probs >= t) for t in thresholds]
    
    best_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_idx]
    best_f1 = f1_scores[best_idx]

    print("=" * 50)
    print(f"Optimal Threshold: {best_threshold:.2f}")
    print(f"Best F1 Score:     {best_f1:.4f}")
    print("=" * 50)
    
    if 0.6 <= best_threshold <= 0.7:
        print("Note: The optimal threshold is in the 0.6 - 0.7 range.")
        print(f"Configure 'CNN_DIRTY_THRESHOLD' to {best_threshold:.2f} during inference to resolve bias.")
    else:
        print(f"We recommend setting 'CNN_DIRTY_THRESHOLD' to {best_threshold:.2f} in your app config.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find optimal CNN threshold by maximizing F1 score.")
    parser.add_argument("--model", type=str, default=r"d:\DuAn\buiban.h5", help="Path to buiban.h5 model weights.")
    parser.add_argument("--val_dir", type=str, required=True, help="Path to validation directory structured with 'sach' and 'ban' subfolders.")
    parser.add_argument("--patch_size", type=int, default=224, help="Image resolution for CNN.")
    
    args = parser.parse_args()
    find_best_threshold(args.model, args.val_dir, args.patch_size)
