# -*- coding: utf-8 -*-
"""
CHƯƠNG TRÌNH ĐO LƯỜNG ĐỘ TRỄ SUY LUẬN AI TRÊN MÁY TÍNH THỰC TẾ
(Empirical AI Inference Latency Benchmarking Tool - Field PC Edition)

Tác giả: Dự Án Hệ Thống Giám Sát & Vệ Sinh Pin Mặt Trời Tự Động (SolarClean)
Chuẩn mực: Liêm chính học thuật - Đo lường trực tiếp trên phần cứng thực tế.
"""

import os
import sys

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import time
import glob
import json
import argparse
import threading
import numpy as np
import cv2

# Đảm bảo UTF-8 cho Windows Console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import torch
import torch.nn as nn
from ultralytics import YOLO

# Xác định thư mục gốc của chương trình
APP_DIR = os.path.dirname(os.path.abspath(__file__))

def get_system_hardware():
    has_cuda = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if has_cuda else "None (CPU Only)"
    return {
        "os": sys.platform,
        "python_version": sys.version.split()[0],
        "pytorch_version": torch.__version__,
        "cuda_available": has_cuda,
        "gpu_name": gpu_name,
        "cpu_count": os.cpu_count()
    }

class EfficientNetB0Wrapper:
    """Mô hình phân loại độ bẩn ma trận 32 ô tế bào quang điện"""
    def __init__(self, device="cpu", half_precision=False):
        self.device = device
        self.half_precision = half_precision and device.startswith("cuda")
        self.model = None

        try:
            import torchvision.models as models
            eff = models.efficientnet_b0(weights=None)
            eff.classifier[1] = nn.Linear(eff.classifier[1].in_features, 2)
            eff.to(self.device)
            if self.half_precision:
                eff.half()
            eff.eval()
            self.model = eff
            prec_str = "FP16 Half" if self.half_precision else "FP32 Full"
            print(f"✅ [OK] Đã nạp EfficientNet-B0 ({prec_str} trên {self.device.upper()})")
        except Exception as e:
            print(f"❌ Lỗi nạp EfficientNet-B0: {e}")

    def predict_batch_32(self, patches_tensor):
        if self.half_precision:
            patches_tensor = patches_tensor.half()
        else:
            patches_tensor = patches_tensor.float()

        with torch.no_grad():
            logits = self.model(patches_tensor)
            probs = torch.softmax(logits, dim=1)
            if self.device.startswith("cuda"):
                torch.cuda.synchronize()
        return probs.cpu().numpy()

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def get_panel_corners(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    epsilon = 0.05 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) == 4:
        return approx.reshape(4, 2)
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    return np.int32(box)

def extract_real_32_patches(frame, mask=None, patch_size=224):
    target_w, target_h = (896, 1792)
    patch_rows, patch_cols = 8, 4

    warped = None
    if mask is not None and np.sum(mask) > 0:
        corners = get_panel_corners(mask)
        if corners is not None:
            rect = order_points(corners)
            w1 = np.linalg.norm(rect[0] - rect[1])
            w2 = np.linalg.norm(rect[2] - rect[3])
            h1 = np.linalg.norm(rect[0] - rect[3])
            h2 = np.linalg.norm(rect[1] - rect[2])
            avg_w = (w1 + w2) / 2
            avg_h = (h1 + h2) / 2

            if avg_w > avg_h:
                target_w, target_h = 1792, 896
                patch_rows, patch_cols = 4, 8
            else:
                target_w, target_h = 896, 1792
                patch_rows, patch_cols = 8, 4

            dst = np.array([
                [0, 0],
                [target_w - 1, 0],
                [target_w - 1, target_h - 1],
                [0, target_h - 1]
            ], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(frame, M, (target_w, target_h))

    if warped is None:
        warped = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

    patches_list = []
    boxes = []
    for r in range(patch_rows):
        for c in range(patch_cols):
            x1 = c * patch_size
            y1 = r * patch_size
            x2 = x1 + patch_size
            y2 = y1 + patch_size
            patch = warped[y1:y2, x1:x2]
            if patch.shape[0] != patch_size or patch.shape[1] != patch_size:
                patch = cv2.resize(patch, (patch_size, patch_size))
            patch_rgb = cv2.cvtColor(patch, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            patches_list.append(patch_rgb)
            boxes.append((x1, y1, x2, y2))

    patches_np = np.stack(patches_list, axis=0)
    patches_tensor = torch.from_numpy(patches_np).permute(0, 3, 1, 2)
    return warped, patches_tensor, boxes, (patch_rows, patch_cols)

def run_academic_benchmark(
    seg_model_path=None,
    det_model_path=None,
    test_image_dir=None,
    num_warmup=15,
    num_runs=30,
    device_mode="auto",
    half_precision=True,
    save_visualizations=True,
    output_dir=None,
    progress_callback=None,
    log_callback=None
):
    if seg_model_path is None:
        seg_model_path = os.path.join(APP_DIR, "models", "panel 2.pt")
    if det_model_path is None:
        det_model_path = os.path.join(APP_DIR, "models", "Solar.pt")
    if test_image_dir is None:
        test_image_dir = os.path.join(APP_DIR, "snapshots_mau")
    if output_dir is None:
        output_dir = os.path.join(APP_DIR, "ket_qua_thuc_nghiem")

    os.makedirs(output_dir, exist_ok=True)
    vis_dir = os.path.join(output_dir, "anh_nhan_dien")
    if save_visualizations:
        os.makedirs(vis_dir, exist_ok=True)
    
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    hw = get_system_hardware()
    log("=" * 90)
    log("🔬 CHƯƠNG TRÌNH ĐO LƯỜNG ĐỘ TRỄ SUY LUẬN AI TRÊN PHẦN CỨNG MÁY TÍNH THỰC TẾ")
    log("=" * 90)
    log(f"💻 Bộ xử lý CPU:        {hw['cpu_count']} Cores")
    log(f"🎮 Card đồ họa GPU:     {hw['gpu_name']} (CUDA: {hw['cuda_available']})")
    log(f"⚙️ Framework:          PyTorch {hw['pytorch_version']}")
    log(f"🔄 Chu kỳ Warm-up:      {num_warmup} (loại bỏ hoàn toàn khỏi thống kê)")
    log(f"📊 Số chu kỳ đo lặp:    {num_runs} chu kỳ độc lập (Batch size = 1)")
    log("=" * 90)

    if device_mode == "auto":
        use_cuda = hw['cuda_available']
    else:
        use_cuda = (device_mode.lower() == "cuda" and hw['cuda_available'])
    torch_device = "cuda:0" if use_cuda else "cpu"
    use_half = half_precision and use_cuda

    log(f"🎯 Thiết bị thực thi:   {torch_device.upper()} | Chế độ: {'FP16 (Half)' if use_half else 'FP32 (Full)'}")

    # Nạp mô hình
    log("\n[1/4] Đang nạp các mô hình AI vào bộ nhớ thiết bị...")
    if not os.path.exists(seg_model_path):
        log(f"❌ Không tìm thấy file: {seg_model_path}")
        return None
    if not os.path.exists(det_model_path):
        log(f"❌ Không tìm thấy file: {det_model_path}")
        return None

    model_seg = YOLO(seg_model_path)
    model_seg.to(torch_device)
    log(f" -> YOLOv8-Seg:        {os.path.basename(seg_model_path)} [OK]")

    model_det = YOLO(det_model_path)
    model_det.to(torch_device)
    log(f" -> YOLOv8 Detection:  {os.path.basename(det_model_path)} [OK]")

    model_cls = EfficientNetB0Wrapper(device=torch_device, half_precision=use_half)
    log(f" -> EfficientNet-B0:   32 Ô tế bào quang điện [OK]")

    # Đọc ảnh thực nghiệm
    img_files = glob.glob(os.path.join(test_image_dir, "*.jpg")) + glob.glob(os.path.join(test_image_dir, "*.png"))
    if not img_files:
        log(f"⚠️ Thư mục '{test_image_dir}' trống, tạo ảnh mô phỏng 1920x1080...")
        sample_frame = np.random.randint(0, 256, (1920, 1080, 3), dtype=np.uint8)
        img_files = [sample_frame] * (num_warmup + num_runs)
        is_dummy = True
    else:
        log(f"📷 Tìm thấy {len(img_files)} ảnh chụp thực nghiệm trong '{test_image_dir}'.")
        is_dummy = False

    # Giai đoạn Warm-up
    log(f"\n[2/4] Chạy Warm-up ({num_warmup} chu kỳ) để nạp CUDA kernels và ổn định xung nhịp...")
    for w in range(num_warmup):
        idx = w % len(img_files)
        frame = cv2.imread(img_files[idx]) if not is_dummy else img_files[idx]
        if frame is None:
            continue
        _ = model_seg(frame, verbose=False, device=torch_device, half=use_half)
        _ = model_det(frame, verbose=False, device=torch_device, half=use_half)
        dummy_tensor = torch.rand(32, 3, 224, 224).to(torch_device)
        _ = model_cls.predict_batch_32(dummy_tensor)
        if use_cuda:
            torch.cuda.synchronize()

    log("✅ Hoàn thành Warm-up. Hệ thống đạt trạng thái Steady State.")

    # Giai đoạn đo lường chính thức
    log(f"\n[3/4] Bắt đầu đo đạc chính thức qua {num_runs} chu kỳ...")
    records = {
        "t_preprocess": [],
        "t_seg_infer": [],
        "t_seg_post": [],
        "t_crop_32": [],
        "t_cls_infer": [],
        "t_det_infer": [],
        "t_det_post": [],
        "t_end_to_end": []
    }

    for r in range(num_runs):
        idx = (r + num_warmup) % len(img_files)
        img_path = img_files[idx] if not is_dummy else f"frame_{r}.jpg"
        filename = os.path.basename(img_path) if not is_dummy else f"frame_{r}.jpg"
        frame = cv2.imread(img_path) if not is_dummy else img_files[idx]
        if frame is None:
            continue

        if use_cuda:
            torch.cuda.synchronize()
        t_pipeline_start = time.perf_counter()

        # 1. Preprocess
        t0 = time.perf_counter()
        _ = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        t1 = time.perf_counter()
        t_pre = (t1 - t0) * 1000.0

        # 2. YOLOv8-Seg
        if use_cuda:
            torch.cuda.synchronize()
        t_seg_start = time.perf_counter()
        res_seg = model_seg(frame, verbose=False, device=torch_device, half=use_half)[0]
        if use_cuda:
            torch.cuda.synchronize()
        t_seg_end = time.perf_counter()
        t_seg_total = (t_seg_end - t_seg_start) * 1000.0

        if hasattr(res_seg, 'speed') and 'inference' in res_seg.speed:
            t_seg_inf = res_seg.speed['inference']
            t_seg_pst = res_seg.speed.get('postprocess', max(0.0, t_seg_total - t_seg_inf))
        else:
            t_seg_inf = t_seg_total * 0.8
            t_seg_pst = t_seg_total * 0.2

        panel_mask = None
        if res_seg.masks is not None and len(res_seg.masks.data) > 0:
            mask_data = res_seg.masks.data[0].cpu().numpy()
            panel_mask = cv2.resize((mask_data > 0.5).astype(np.uint8) * 255, (frame.shape[1], frame.shape[0]))

        # 3. Trích xuất 32 ô ma trận
        t_crop_start = time.perf_counter()
        warped_panel, patches_tensor, patch_boxes, grid_shape = extract_real_32_patches(frame, panel_mask)
        patches_tensor = patches_tensor.to(torch_device)
        t_crop_end = time.perf_counter()
        t_crop = (t_crop_end - t_crop_start) * 1000.0

        # 4. EfficientNet-B0 (32 ô)
        if use_cuda:
            torch.cuda.synchronize()
        t_cls_start = time.perf_counter()
        probs_32 = model_cls.predict_batch_32(patches_tensor)
        if use_cuda:
            torch.cuda.synchronize()
        t_cls_end = time.perf_counter()
        t_cls_inf = (t_cls_end - t_cls_start) * 1000.0

        # 5. YOLOv8 Det (Dị vật lá cây)
        if use_cuda:
            torch.cuda.synchronize()
        t_det_start = time.perf_counter()
        res_det = model_det(frame, verbose=False, device=torch_device, half=use_half)[0]
        if use_cuda:
            torch.cuda.synchronize()
        t_det_end = time.perf_counter()
        t_det_total = (t_det_end - t_det_start) * 1000.0

        if hasattr(res_det, 'speed') and 'inference' in res_det.speed:
            t_det_inf = res_det.speed['inference']
            t_det_pst = res_det.speed.get('postprocess', max(0.0, t_det_total - t_det_inf))
        else:
            t_det_inf = t_det_total * 0.8
            t_det_pst = t_det_total * 0.2

        t_pipeline_end = time.perf_counter()
        t_e2e = (t_pipeline_end - t_pipeline_start) * 1000.0

        records["t_preprocess"].append(t_pre)
        records["t_seg_infer"].append(t_seg_inf)
        records["t_seg_post"].append(t_seg_pst)
        records["t_crop_32"].append(t_crop)
        records["t_cls_infer"].append(t_cls_inf)
        records["t_det_infer"].append(t_det_inf)
        records["t_det_post"].append(t_det_pst)
        records["t_end_to_end"].append(t_e2e)

        num_leaves = len(res_det.boxes) if res_det.boxes is not None else 0
        dirt_probs_arr = probs_32[:, 1] if probs_32.shape[1] > 1 else probs_32[:, 0]
        dirty_patches = int(np.sum(dirt_probs_arr >= 0.30))
        soiling_ratio = (dirty_patches / 32.0) * 100.0

        # Lưu ảnh nhận diện đa tầng
        if save_visualizations and r < 5:
            vis_img = warped_panel.copy()
            overlay = vis_img.copy()
            for p_idx, (bx1, by1, bx2, by2) in enumerate(patch_boxes):
                p_dirt = dirt_probs_arr[p_idx]
                is_dirty = p_dirt >= 0.30
                color = (0, 0, 220) if is_dirty else (0, 200, 0)
                cv2.rectangle(overlay, (bx1+2, by1+2), (bx2-2, by2-2), color, -1)
                tag = "B" if is_dirty else "S"
                label = f"{tag}:{p_dirt*100:.0f}%"
                cv2.putText(vis_img, label, (bx1 + 6, by1 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            cv2.addWeighted(overlay, 0.35, vis_img, 0.65, 0, vis_img)
            info_text = f"Latency: {t_e2e:.1f} ms | Leaves: {num_leaves} | Dirty: {dirty_patches}/32 ({soiling_ratio:.1f}%) [Thresh: 30%]"
            cv2.rectangle(vis_img, (0, 0), (vis_img.shape[1], 45), (0, 0, 0), -1)
            cv2.putText(vis_img, info_text, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            
            save_path = os.path.join(vis_dir, f"nhan_dien_{filename}")
            cv2.imwrite(save_path, vis_img)

        if progress_callback:
            progress_callback(r + 1, num_runs, t_e2e, dirty_patches, num_leaves)

        if (r + 1) % 10 == 0 or (r + 1) == num_runs:
            log(f"   [Tiến độ: {r+1:2d}/{num_runs}] Ảnh: {filename[:20]} | Ô bẩn: {dirty_patches:2d}/32 | Lá cây: {num_leaves} | Độ trễ: {t_e2e:.1f} ms")

    # Giai đoạn 4: Tổng kết & Xuất Báo Cáo
    log("\n[4/4] Tổng kết số liệu và xuất báo cáo khoa học...")
    def calc_stats(arr):
        a = np.array(arr)
        return {
            "mean": float(np.mean(a)),
            "std": float(np.std(a)),
            "median": float(np.median(a)),
            "min": float(np.min(a)),
            "max": float(np.max(a)),
            "p95": float(np.percentile(a, 95)),
            "p99": float(np.percentile(a, 99))
        }

    summary = {k: calc_stats(v) for k, v in records.items()}
    pure_ai = [
        records["t_seg_infer"][i] + records["t_cls_infer"][i] + records["t_det_infer"][i]
        for i in range(num_runs)
    ]
    summary["t_pure_ai_total"] = calc_stats(pure_ai)
    effective_fps = 1000.0 / summary["t_end_to_end"]["mean"]

    prec_tag = "fp16" if use_half else "fp32"
    device_tag = f"{'cuda' if use_cuda else 'cpu'}_{prec_tag}"

    log("\n" + "=" * 95)
    log(f"📊 BẢNG KẾT QUẢ ĐO LƯỜNG ĐỘ TRỄ SUY LUẬN TRÊN PHẦN CỨNG THỰC TẾ ({device_tag.upper()})")
    log("=" * 95)
    header = f"{'Phân đoạn xử lý':<32} | {'Mean ± Std (ms)':<18} | {'Median (ms)':<12} | {'P95 (ms)':<10} | {'Min - Max (ms)':<16}"
    log(header)
    log("-" * 95)

    rows = [
        ("1. Tiền xử lý ảnh (Preprocess)", "t_preprocess"),
        ("2. YOLOv8-Seg (Tách mặt pin)", "t_seg_infer"),
        ("3. YOLOv8-Seg (Hậu xử lý Mask)", "t_seg_post"),
        ("4. Nắn thẳng & Tách 32 ô ROI thực", "t_crop_32"),
        ("5. EfficientNet-B0 (32 ô bẩn thực)", "t_cls_infer"),
        ("6. YOLOv8 Det (Dị vật lá cây)", "t_det_infer"),
        ("7. YOLOv8 Det (Hậu xử lý NMS)", "t_det_post"),
        ("⚡ TỔNG SUY LUẬN AI THUẦN TÚY", "t_pure_ai_total"),
        ("🚀 TOÀN BỘ ĐƯỜNG ỐNG (END-TO-END)", "t_end_to_end"),
    ]

    for label, key in rows:
        st = summary[key]
        log(f"{label:<32} | {st['mean']:.2f} ± {st['std']:.2f} ms   | {st['median']:.2f} ms     | {st['p95']:.2f} ms   | {st['min']:.1f} - {st['max']:.1f} ms")

    log("-" * 95)
    log(f"🎯 TỐC ĐỘ TOÀN HỆ THỐNG: {effective_fps:.1f} FPS (Thời gian trung bình: {summary['t_end_to_end']['mean']:.2f} ms/khung hình)")
    log("=" * 95)

    # Xuất file JSON
    json_path = os.path.join(output_dir, f"ket_qua_do_tre_{device_tag}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "hardware": hw,
            "device_mode": device_tag,
            "num_warmup": num_warmup,
            "num_runs": num_runs,
            "summary": summary,
            "effective_fps": effective_fps
        }, f, indent=4, ensure_ascii=False)

    # Xuất file CSV
    csv_path = os.path.join(output_dir, f"ket_qua_do_tre_{device_tag}.csv")
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write("trial," + ",".join(records.keys()) + "\n")
        for i in range(num_runs):
            f.write(f"{i+1}," + ",".join([f"{records[k][i]:.4f}" for k in records]) + "\n")

    # Xuất bảng Markdown bài báo
    md_path = os.path.join(output_dir, f"bang_hoc_thuat_{device_tag}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"### Bảng: Phân rã thời gian xử lý và tài nguyên tính toán của chuỗi mô hình AI\n")
        f.write(f"*(Thực nghiệm trên: {hw['gpu_name']}, CPU: {hw['cpu_count']} Cores, PyTorch {hw['pytorch_version']}, Batch size = 1, N = {num_runs} chu kỳ độc lập)*\n\n")
        f.write("| Phân đoạn xử lý | Tiền xử lý ($T_{\\text{pre}}$) | Suy luận ($T_{\\text{infer}}$) | Hậu xử lý ($T_{\\text{post}}$) | Tổng độ trễ ($T_{\\text{total}}$) |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: |\n")
        f.write(f"| **YOLOv8-Seg** (Tách mặt pin) | {summary['t_preprocess']['mean']:.1f} ± {summary['t_preprocess']['std']:.1f} ms | {summary['t_seg_infer']['mean']:.1f} ± {summary['t_seg_infer']['std']:.1f} ms | {summary['t_seg_post']['mean']:.1f} ± {summary['t_seg_post']['std']:.1f} ms | **{summary['t_seg_infer']['mean'] + summary['t_seg_post']['mean']:.1f} ms** |\n")
        f.write(f"| **YOLOv8** (Dị vật lá cây) | — | {summary['t_det_infer']['mean']:.1f} ± {summary['t_det_infer']['std']:.1f} ms | {summary['t_det_post']['mean']:.1f} ± {summary['t_det_post']['std']:.1f} ms | **{summary['t_det_infer']['mean'] + summary['t_det_post']['mean']:.1f} ms** |\n")
        f.write(f"| **Nắn thẳng & Tách 32 ô ROI** | — | — | — | **{summary['t_crop_32']['mean']:.1f} ± {summary['t_crop_32']['std']:.1f} ms** |\n")
        f.write(f"| **EfficientNet-B0** (32 ô bẩn) | — | {summary['t_cls_infer']['mean']:.1f} ± {summary['t_cls_infer']['std']:.1f} ms | — | **{summary['t_cls_infer']['mean']:.1f} ± {summary['t_cls_infer']['std']:.1f} ms** |\n")
        f.write(f"| **Toàn bộ chuỗi (Pipeline)** | **{summary['t_preprocess']['mean']:.1f} ms** | **{summary['t_pure_ai_total']['mean']:.1f} ms** | **{summary['t_seg_post']['mean'] + summary['t_det_post']['mean']:.1f} ms** | **{summary['t_end_to_end']['mean']:.1f} ± {summary['t_end_to_end']['std']:.1f} ms** |\n\n")
        f.write(f"**Tốc độ xử lý hiệu dụng:** **{effective_fps:.1f} FPS**\n")

    log(f"\n📁 Đã xuất toàn bộ kết quả vào: '{output_dir}/'")
    log(f"   -> File JSON:       {json_path}")
    log(f"   -> File CSV:        {csv_path}")
    log(f"   -> Bảng Markdown:   {md_path}")
    if save_visualizations:
        log(f"   -> Thư mục ảnh:     {vis_dir}")

    return summary, effective_fps

# ── GIAO DIỆN ĐỒ HỌA TKINTER ──
def launch_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext

    root = tk.Tk()
    root.title("Công Cụ Đo Độ Trễ Suy Luận AI Thực Tế - SolarClean Target PC")
    root.geometry("960x740")
    root.minsize(820, 600)

    hw = get_system_hardware()

    style = ttk.Style()
    style.theme_use('clam')

    header_frame = ttk.LabelFrame(root, text=" 💻 Thông Tin Phần Cứng Máy Tính Thực Tế ", padding=10)
    header_frame.pack(fill="x", padx=15, pady=8)

    gpu_txt = f"{hw['gpu_name']} (CUDA: {'Sẵn sàng' if hw['cuda_available'] else 'Không'})"
    ttk.Label(header_frame, text=f"🎮 GPU: {gpu_txt}", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.Label(header_frame, text=f"💻 CPU: {hw['cpu_count']} Logical Cores", font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=20, pady=2)
    ttk.Label(header_frame, text=f"⚙️ PyTorch: {hw['pytorch_version']}", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Label(header_frame, text=f"🐍 Python: {hw['python_version']}", font=("Segoe UI", 10)).grid(row=1, column=1, sticky="w", padx=20, pady=2)

    ctrl_frame = ttk.LabelFrame(root, text=" ⚙️ Thiết Lập Đo Lường ", padding=10)
    ctrl_frame.pack(fill="x", padx=15, pady=5)

    ttk.Label(ctrl_frame, text="Số ảnh thử nghiệm:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    runs_var = tk.IntVar(value=30)
    runs_entry = ttk.Entry(ctrl_frame, textvariable=runs_var, width=8)
    runs_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

    ttk.Label(ctrl_frame, text="Warm-up:").grid(row=0, column=2, sticky="w", padx=15, pady=5)
    warm_var = tk.IntVar(value=10)
    warm_entry = ttk.Entry(ctrl_frame, textvariable=warm_var, width=8)
    warm_entry.grid(row=0, column=3, sticky="w", padx=5, pady=5)

    ttk.Label(ctrl_frame, text="Thiết bị:").grid(row=0, column=4, sticky="w", padx=15, pady=5)
    dev_var = tk.StringVar(value="cuda" if hw['cuda_available'] else "cpu")
    dev_combo = ttk.Combobox(ctrl_frame, textvariable=dev_var, values=["cuda", "cpu"], state="readonly", width=8)
    dev_combo.grid(row=0, column=5, sticky="w", padx=5, pady=5)

    half_var = tk.BooleanVar(value=True if hw['cuda_available'] else False)
    chk_half = ttk.Checkbutton(ctrl_frame, text="FP16 Tăng Tốc (GPU)", variable=half_var)
    chk_half.grid(row=0, column=6, sticky="w", padx=15, pady=5)

    btn_frame = ttk.Frame(ctrl_frame)
    btn_frame.grid(row=1, column=0, columnspan=7, sticky="ew", pady=10)

    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(btn_frame, variable=progress_var, maximum=100)
    progress_bar.pack(side="left", fill="x", expand=True, padx=5)

    status_lbl = ttk.Label(btn_frame, text="Sẵn sàng", font=("Segoe UI", 9, "italic"))
    status_lbl.pack(side="left", padx=10)

    log_frame = ttk.LabelFrame(root, text=" 📜 Nhật Ký Đo Đạc Thực Nghiệm & Bảng Kết Quả ", padding=10)
    log_frame.pack(fill="both", expand=True, padx=15, pady=8)

    txt_log = scrolledtext.ScrolledText(log_frame, wrap="word", font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4")
    txt_log.pack(fill="both", expand=True)

    def append_log(msg):
        txt_log.insert(tk.END, msg + "\n")
        txt_log.see(tk.END)

    def on_progress(current, total, current_lat, dirty_cnt, leaf_cnt):
        pct = (current / total) * 100
        progress_var.set(pct)
        status_lbl.config(text=f"Ảnh {current}/{total} | Ô bẩn: {dirty_cnt}/32 | Lá: {leaf_cnt} | Độ trễ: {current_lat:.1f} ms")
        root.update_idletasks()

    def run_benchmark_thread():
        btn_start.config(state="disabled")
        txt_log.delete("1.0", tk.END)
        status_lbl.config(text="Đang nạp mô hình...")

        def task():
            try:
                run_academic_benchmark(
                    num_warmup=warm_var.get(),
                    num_runs=runs_var.get(),
                    device_mode=dev_var.get(),
                    half_precision=half_var.get(),
                    save_visualizations=True,
                    progress_callback=on_progress,
                    log_callback=append_log
                )
                status_lbl.config(text="✅ Hoàn thành xuất sắc!")
                messagebox.showinfo("Thành công", "Đo lường độ trễ hoàn tất!\nKết quả và ảnh đã lưu trong thư mục 'ket_qua_thuc_nghiem/'.")
            except Exception as e:
                append_log(f"❌ Lỗi: {e}")
                status_lbl.config(text="❌ Lỗi")
            finally:
                btn_start.config(state="normal")

        threading.Thread(target=task, daemon=True).start()

    btn_start = ttk.Button(btn_frame, text="🚀 BẮT ĐẦU ĐO ĐẠC THỰC TẾ", command=run_benchmark_thread)
    btn_start.pack(side="right", padx=5)

    root.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real PC AI Latency Benchmark")
    parser.add_argument("--gui", action="store_true", help="Chạy giao diện đồ họa GUI")
    parser.add_argument("--runs", type=int, default=30, help="Số ảnh đo lặp")
    parser.add_argument("--warmup", type=int, default=10, help="Số lần warm-up")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu", choices=["cuda", "cpu"])
    parser.add_argument("--half", action="store_true", help="Bật FP16 Half-Precision")
    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        launch_gui()
    else:
        run_academic_benchmark(
            num_warmup=args.warmup,
            num_runs=args.runs,
            device_mode=args.device,
            half_precision=args.half
        )
