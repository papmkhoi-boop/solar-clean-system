# -*- coding: utf-8 -*-
"""
HỆ THỐNG ĐO LƯỜNG ĐỘ TRỄ VÀ TRỰC QUAN HÓA SUY LUẬN AI THỰC NGHIỆM
(SolarClean Empirical Latency & Multi-Stage Edge-AI Benchmarking Suite)

Chuẩn mực: Liêm chính học thuật - Trình bày chuẩn tạp chí quốc tế (IEEE / TNU JST)
Tác giả: Dự Án Hệ Thống Tự Động Giám Sát & Vệ Sinh Pin Mặt Trời (SolarClean)
"""

import os
import sys

os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import time
import glob
import json
import csv
import threading
import numpy as np
import cv2

# Đảm bảo UTF-8 cho console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import torch
import torch.nn as nn
from ultralytics import YOLO

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from PIL import Image, ImageTk

# Xác định thư mục ứng dụng
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(APP_DIR, "models")
SNAPSHOTS_DIR = os.path.join(APP_DIR, "snapshots_mau")
RESULTS_DIR = os.path.join(APP_DIR, "ket_qua_thuc_nghiem")
os.makedirs(RESULTS_DIR, exist_ok=True)


def get_hardware_info():
    has_cuda = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if has_cuda else "Không có GPU rời (CPU Only)"
    return {
        "os": sys.platform,
        "python_version": sys.version.split()[0],
        "pytorch_version": torch.__version__,
        "cuda_available": has_cuda,
        "gpu_name": gpu_name,
        "cpu_count": os.cpu_count() or 4
    }


class EfficientNetB0Wrapper:
    """Mô hình phân loại độ bẩn ma trận 32 ô tế bào quang điện (PyTorch Inference)"""
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
        except Exception as e:
            print(f"Lỗi khởi tạo EfficientNet-B0: {e}")

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
    """Sắp xếp 4 điểm góc: Top-Left (1), Top-Right (2), Bottom-Right (3), Bottom-Left (4)"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def get_panel_corners(mask):
    """Trích xuất 4 góc của bề mặt tấm pin từ mặt nạ phân đoạn"""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None
    cnt = max(contours, key=cv2.contourArea)
    epsilon = 0.03 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True)
    if len(approx) == 4:
        return order_points(approx.reshape(4, 2)), cnt
    rect = cv2.minAreaRect(cnt)
    box = cv2.boxPoints(rect)
    return order_points(box), cnt


def warp_panel(image, corners, target_w=896, target_h=448):
    """Nắn phẳng phối cảnh hình học (Perspective Transform) bề mặt pin"""
    dst = np.array([
        [0, 0],
        [target_w - 1, 0],
        [target_w - 1, target_h - 1],
        [0, target_h - 1]
    ], dtype="float32")
    M = cv2.getPerspectiveTransform(corners, dst)
    warped = cv2.warpPerspective(image, M, (target_w, target_h))
    return warped, M


def slice_into_32_cells(warped_img, rows=4, cols=8):
    """Phân rã mặt pin đã nắn thành 32 ô tế bào quang điện (4 hàng x 8 cột)"""
    h, w, _ = warped_img.shape
    cell_h = h // rows
    cell_w = w // cols
    cells = []
    coords = []
    for r in range(rows):
        for c in range(cols):
            y1, y2 = r * cell_h, (r + 1) * cell_h
            x1, x2 = c * cell_w, (c + 1) * cell_w
            cell_patch = warped_img[y1:y2, x1:x2]
            cell_patch_resized = cv2.resize(cell_patch, (224, 224))
            cells.append(cell_patch_resized)
            coords.append((x1, y1, x2, y2))
    return cells, coords


class LatencyBenchmarkGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SolarClean AI Latency & Inference Benchmark Suite (IEEE / TNU JST)")
        self.root.geometry("1420x920")
        self.root.minsize(1220, 780)

        self.hw = get_hardware_info()
        self.is_running = False
        self.stop_requested = False
        self.benchmark_records = []
        self.last_inference_result = None

        self.model_seg = None
        self.model_det = None
        self.model_eff = None
        self.loaded_device = None
        self.loaded_half = None

        self._setup_style()
        self._build_ui()
        self._load_snapshot_list()

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        self.root.configure(bg="#0f172a")

        style.configure(".", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 9))
        style.configure("TFrame", background="#0f172a")
        style.configure("TLabelframe", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background="#1e293b", foreground="#38bdf8", font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 9))
        
        style.configure("TCombobox", fieldbackground="#334155", background="#1e293b", foreground="#ffffff")
        style.configure("TEntry", fieldbackground="#334155", foreground="#ffffff")

        style.configure("Treeview", background="#1e293b", foreground="#f8fafc", fieldbackground="#1e293b", rowheight=24, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#334155", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#0284c7")])

    def _build_ui(self):
        # 1. Header Frame
        header_frame = tk.Frame(self.root, bg="#0f172a", pady=6, padx=16)
        header_frame.pack(fill="x")

        lbl_title = tk.Label(header_frame, text="HỆ THỐNG ĐO LƯỜNG ĐỘ TRỄ SUY LUẬN AI & TRỰC QUAN HÓA THỰC NGHIỆM", font=("Segoe UI", 12, "bold"), bg="#0f172a", fg="#38bdf8")
        lbl_title.pack(side="left")

        hw_text = f"Phần cứng: {self.hw['gpu_name']} | PyTorch: {self.hw['pytorch_version']} | CPU: {self.hw['cpu_count']} Cores"
        lbl_hw = tk.Label(header_frame, text=hw_text, font=("Segoe UI", 9), bg="#0f172a", fg="#94a3b8")
        lbl_hw.pack(side="right")

        # 2. Main Container
        main_container = tk.Frame(self.root, bg="#0f172a", padx=12, pady=2)
        main_container.pack(fill="both", expand=True)

        # Controls Frame
        ctrl_frame = tk.LabelFrame(main_container, text=" Thiết Lập Thực Nghiệm & Tham Số Ngưỡng Quyết Định ", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 10, "bold"), padx=10, pady=6)
        ctrl_frame.pack(fill="x", pady=3)

        # Row 0: Inputs & Threshold Slider
        row0 = tk.Frame(ctrl_frame, bg="#1e293b")
        row0.pack(fill="x", pady=2)

        tk.Label(row0, text="Thiết bị:", bg="#1e293b", fg="#e2e8f0").pack(side="left", padx=4)
        self.device_var = tk.StringVar(value="cuda" if self.hw['cuda_available'] else "cpu")
        self.cb_device = ttk.Combobox(row0, textvariable=self.device_var, values=["cuda", "cpu"], state="readonly", width=7)
        self.cb_device.pack(side="left", padx=4)

        self.half_var = tk.BooleanVar(value=True if self.hw['cuda_available'] else False)
        self.chk_half = tk.Checkbutton(row0, text="FP16 Half-Precision (GPU)", variable=self.half_var, bg="#1e293b", fg="#38bdf8", selectcolor="#0f172a", activebackground="#1e293b", activeforeground="#38bdf8")
        self.chk_half.pack(side="left", padx=6)

        tk.Label(row0, text="Số mẫu thử (N):", bg="#1e293b", fg="#e2e8f0").pack(side="left", padx=6)
        self.runs_var = tk.IntVar(value=30)
        self.entry_runs = tk.Entry(row0, textvariable=self.runs_var, width=5, bg="#334155", fg="#ffffff", insertbackground="#ffffff")
        self.entry_runs.pack(side="left", padx=2)

        tk.Label(row0, text="Chu kỳ Warm-up:", bg="#1e293b", fg="#e2e8f0").pack(side="left", padx=6)
        self.warm_var = tk.IntVar(value=10)
        self.entry_warm = tk.Entry(row0, textvariable=self.warm_var, width=5, bg="#334155", fg="#ffffff", insertbackground="#ffffff")
        self.entry_warm.pack(side="left", padx=2)

        # Ngưỡng tin cậy bẩn (Tau)
        tk.Label(row0, text="Ngưỡng bẩn (τ):", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#f59e0b").pack(side="left", padx=(14, 4))
        self.dirt_threshold_var = tk.DoubleVar(value=30.0)
        self.slider_thresh = tk.Scale(row0, from_=5.0, to=90.0, resolution=1.0, orient="horizontal", variable=self.dirt_threshold_var, bg="#1e293b", fg="#f59e0b", highlightthickness=0, length=120, command=self._on_threshold_changed)
        self.slider_thresh.pack(side="left", padx=2)
        
        self.lbl_thresh_val = tk.Label(row0, text="30%", font=("Segoe UI", 9, "bold"), bg="#1e293b", fg="#f59e0b", width=4)
        self.lbl_thresh_val.pack(side="left", padx=2)

        tk.Label(row0, text="Ảnh mẫu:", bg="#1e293b", fg="#e2e8f0").pack(side="left", padx=6)
        self.snapshot_var = tk.StringVar()
        self.cb_snapshot = ttk.Combobox(row0, textvariable=self.snapshot_var, state="readonly", width=16)
        self.cb_snapshot.pack(side="left", padx=4)
        self.cb_snapshot.bind("<<ComboboxSelected>>", self._on_snapshot_selected)

        # Row 1: Action Buttons
        row1 = tk.Frame(ctrl_frame, bg="#1e293b")
        row1.pack(fill="x", pady=4)

        self.btn_single = tk.Button(row1, text="Suy Luận 1 Ảnh", bg="#0284c7", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=12, pady=4, cursor="hand2", command=self.run_single_inference_thread)
        self.btn_single.pack(side="left", padx=4)

        self.btn_benchmark = tk.Button(row1, text="Bắt Đầu Đo Lường (Batch)", bg="#10b981", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=14, pady=4, cursor="hand2", command=self.run_benchmark_thread)
        self.btn_benchmark.pack(side="left", padx=6)

        self.btn_stop = tk.Button(row1, text="Dừng", bg="#ef4444", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, state="disabled", cursor="hand2", command=self.stop_process)
        self.btn_stop.pack(side="left", padx=4)

        self.btn_browse = tk.Button(row1, text="Chọn Ảnh Bên Ngoài...", bg="#475569", fg="#ffffff", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=self.browse_custom_image)
        self.btn_browse.pack(side="left", padx=6)

        self.btn_save_fig = tk.Button(row1, text="Xuất Ảnh Minh Chứng Bài Báo", bg="#0ea5e9", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=self.save_figure_for_paper)
        self.btn_save_fig.pack(side="left", padx=6)

        self.btn_export = tk.Button(row1, text="Xuất Báo Cáo CSV / TXT", bg="#8b5cf6", fg="#ffffff", font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=4, cursor="hand2", command=self.export_report)
        self.btn_export.pack(side="right", padx=4)

        self.btn_open_folder = tk.Button(row1, text="Thư Mục Kết Quả", bg="#334155", fg="#e2e8f0", font=("Segoe UI", 9), relief="flat", padx=10, pady=4, cursor="hand2", command=self.open_results_folder)
        self.btn_open_folder.pack(side="right", padx=4)

        # 3. Middle Section: MULTI-STAGE VISUAL PANELS (Left) + SCHOLARLY METRICS CARDS (Right)
        mid_frame = tk.Frame(main_container, bg="#0f172a")
        mid_frame.pack(fill="x", pady=3)

        # Vision Panels Container
        vision_frame = tk.LabelFrame(mid_frame, text=" Chu Trình Xử Lý Thị Giác AI Đa Tầng (Multi-Stage Vision Pipeline) ", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold"), padx=6, pady=6)
        vision_frame.pack(side="left", fill="both", expand=True, padx=3)

        img_grid = tk.Frame(vision_frame, bg="#1e293b")
        img_grid.pack(fill="both", expand=True)

        # Stage 1 View
        panel1 = tk.Frame(img_grid, bg="#0f172a", relief="solid", bd=1, highlightbackground="#334155", highlightthickness=1)
        panel1.grid(row=0, column=0, padx=3, pady=2, sticky="nsew")
        tk.Label(panel1, text="(a) Ảnh Gốc & Biên Phân Đoạn (YOLOv8-Seg)", font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#38bdf8").pack(anchor="w", padx=4, pady=2)
        self.lbl_img_stage1 = tk.Label(panel1, bg="#0f172a", text="Ảnh Camera Gốc", font=("Segoe UI", 9), fg="#64748b", width=35, height=13)
        self.lbl_img_stage1.pack(fill="both", expand=True, padx=2, pady=2)

        # Stage 2 View
        panel2 = tk.Frame(img_grid, bg="#0f172a", relief="solid", bd=1, highlightbackground="#334155", highlightthickness=1)
        panel2.grid(row=0, column=1, padx=3, pady=2, sticky="nsew")
        tk.Label(panel2, text="(b) Mặt Pin Nắn Thẳng Hình Học (Warped ROI)", font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#f59e0b").pack(anchor="w", padx=4, pady=2)
        self.lbl_img_stage2 = tk.Label(panel2, bg="#0f172a", text="Đầu ra nắn phối cảnh\n(Perspective Warp 896x448)", font=("Segoe UI", 9), fg="#64748b", width=35, height=13)
        self.lbl_img_stage2.pack(fill="both", expand=True, padx=2, pady=2)

        # Stage 3 View
        panel3 = tk.Frame(img_grid, bg="#0f172a", relief="solid", bd=1, highlightbackground="#334155", highlightthickness=1)
        panel3.grid(row=0, column=2, padx=3, pady=2, sticky="nsew")
        tk.Label(panel3, text="(c) Bản Đồ Phân Loại 32 Ô (EfficientNet-B0)", font=("Segoe UI", 8, "bold"), bg="#0f172a", fg="#10b981").pack(anchor="w", padx=4, pady=2)
        self.lbl_img_stage3 = tk.Label(panel3, bg="#0f172a", text="Bản đồ ma trận 32 ô\n(Xanh: Sạch | Đỏ: Bẩn >= τ)", font=("Segoe UI", 9), fg="#64748b", width=35, height=13)
        self.lbl_img_stage3.pack(fill="both", expand=True, padx=2, pady=2)

        img_grid.grid_columnconfigure(0, weight=1)
        img_grid.grid_columnconfigure(1, weight=1)
        img_grid.grid_columnconfigure(2, weight=1)

        # Scholarly Metrics Dashboard (Right Panel - Designed for Paper Screenshot)
        cards_frame = tk.LabelFrame(mid_frame, text=" Thông Số Đo Lường & Trạng Thái Thực Nghiệm ", bg="#1e293b", fg="#38bdf8", font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        cards_frame.pack(side="right", fill="y", padx=3)

        self.card_seg = self._create_metric_card(cards_frame, "1. Phân đoạn & Nắn góc (YOLOv8-Seg)", "0.00 ms", "#38bdf8")
        self.card_eff = self._create_metric_card(cards_frame, "2. Phân loại 32 ô lưới (EfficientNet-B0)", "0.00 ms", "#c084fc")
        self.card_det = self._create_metric_card(cards_frame, "3. Phát hiện vật thể cản quang (YOLOv8-Det)", "0.00 ms", "#fbbf24")
        self.card_tot = self._create_metric_card(cards_frame, "TỔNG ĐỘ TRỄ SUY LUẬN TOÀN TRÌNH (E2E)", "0.00 ms  (0.0 FPS)", "#34d399", highlight=True)
        self.card_res = self._create_metric_card(cards_frame, "Diện tích che khuất bề mặt", "Ô bẩn: 0/32 | Dị vật: 0 | Tỷ lệ: 0.0%", "#f87171")
        self.card_decision = self._create_metric_card(cards_frame, "Quyết định điều khiển hệ thống", "CHỜ SUY LUẬN", "#38bdf8", highlight=True)

        # 4. Bottom Section: Progress + Tabs (Data Table & Console Log)
        bottom_frame = tk.Frame(main_container, bg="#0f172a")
        bottom_frame.pack(fill="both", expand=True, pady=2)

        # Progress bar & status
        prog_box = tk.Frame(bottom_frame, bg="#0f172a")
        prog_box.pack(fill="x", pady=1)

        self.progress_var = tk.DoubleVar(value=0)
        self.prog_bar = ttk.Progressbar(prog_box, variable=self.progress_var, maximum=100)
        self.prog_bar.pack(side="left", fill="x", expand=True, padx=4)

        self.lbl_status = tk.Label(prog_box, text="Hệ thống sẵn sàng thực hiện đo lường.", font=("Segoe UI", 9, "italic"), bg="#0f172a", fg="#38bdf8")
        self.lbl_status.pack(side="right", padx=6)

        # Notebook tabs
        self.notebook = ttk.Notebook(bottom_frame)
        self.notebook.pack(fill="both", expand=True, pady=1)

        # Tab 1: Live Results Table
        tab_table = tk.Frame(self.notebook, bg="#1e293b")
        self.notebook.add(tab_table, text=" Bảng Dữ Liệu Từng Chu Kỳ Thực Nghiệm (Empirical Runs) ")

        cols = ("idx", "filename", "seg_lat", "eff_lat", "det_lat", "total_lat", "fps", "dirty_cells", "leaf_cnt", "dirty_pct", "decision")
        self.tree = ttk.Treeview(tab_table, columns=cols, show="headings", height=6)
        self.tree.heading("idx", text="#")
        self.tree.heading("filename", text="Tên Mẫu Ảnh")
        self.tree.heading("seg_lat", text="YOLOv8-Seg (ms)")
        self.tree.heading("eff_lat", text="EfficientNet-B0 (ms)")
        self.tree.heading("det_lat", text="YOLOv8-Det (ms)")
        self.tree.heading("total_lat", text="Tổng Độ Trễ (ms)")
        self.tree.heading("fps", text="FPS")
        self.tree.heading("dirty_cells", text="Số Ô Bẩn (/32)")
        self.tree.heading("leaf_cnt", text="Dị Vật")
        self.tree.heading("dirty_pct", text="Tỷ Lệ Bẩn (%)")
        self.tree.heading("decision", text="Quyết Định")

        self.tree.column("idx", width=35, anchor="center")
        self.tree.column("filename", width=170, anchor="w")
        self.tree.column("seg_lat", width=105, anchor="center")
        self.tree.column("eff_lat", width=125, anchor="center")
        self.tree.column("det_lat", width=110, anchor="center")
        self.tree.column("total_lat", width=115, anchor="center")
        self.tree.column("fps", width=65, anchor="center")
        self.tree.column("dirty_cells", width=95, anchor="center")
        self.tree.column("leaf_cnt", width=65, anchor="center")
        self.tree.column("dirty_pct", width=95, anchor="center")
        self.tree.column("decision", width=110, anchor="center")

        sb_v = ttk.Scrollbar(tab_table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb_v.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb_v.pack(side="right", fill="y")

        # Tab 2: Console Log & Academic Summary
        tab_log = tk.Frame(self.notebook, bg="#1e293b")
        self.notebook.add(tab_log, text=" Bảng Thống Kê Học Thuật & Nhật Ký Hệ Thống (IEEE / TNU JST) ")

        self.txt_log = scrolledtext.ScrolledText(tab_log, wrap="word", font=("Consolas", 9), bg="#0f172a", fg="#e2e8f0", insertbackground="#ffffff")
        self.txt_log.pack(fill="both", expand=True, padx=4, pady=4)

    def _create_metric_card(self, parent, title, initial_val, color, highlight=False):
        card = tk.Frame(parent, bg="#0f172a" if highlight else "#1e293b", padx=8, pady=4, relief="solid", bd=1, highlightbackground=color, highlightthickness=1)
        card.pack(fill="x", pady=2)

        lbl_title = tk.Label(card, text=title, font=("Segoe UI", 8, "bold" if highlight else "normal"), bg=card["bg"], fg="#94a3b8")
        lbl_title.pack(anchor="w")

        lbl_val = tk.Label(card, text=initial_val, font=("Consolas" if "ms" in initial_val else "Segoe UI", 11 if not highlight else 12, "bold"), bg=card["bg"], fg=color)
        lbl_val.pack(anchor="w")
        return lbl_val

    def log(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def _on_threshold_changed(self, val):
        t_val = float(val)
        self.lbl_thresh_val.config(text=f"{t_val:.0f}%")
        if self.last_inference_result is not None:
            self._recompute_and_update_display_with_threshold(t_val / 100.0)

    def _load_snapshot_list(self):
        snapshots = sorted(glob.glob(os.path.join(SNAPSHOTS_DIR, "*.jpg")) + glob.glob(os.path.join(SNAPSHOTS_DIR, "*.png")))
        names = [os.path.basename(f) for f in snapshots]
        if names:
            self.cb_snapshot["values"] = names
            self.cb_snapshot.current(0)
            self.log(f"Đã nạp {len(names)} mẫu ảnh thực nghiệm từ thư mục: '{SNAPSHOTS_DIR}'.")
        else:
            self.cb_snapshot["values"] = ["Không tìm thấy ảnh"]
            self.log(f"Cảnh báo: Không tìm thấy ảnh trong '{SNAPSHOTS_DIR}'.")

    def _on_snapshot_selected(self, event=None):
        selected_name = self.snapshot_var.get()
        img_path = os.path.join(SNAPSHOTS_DIR, selected_name)
        if os.path.exists(img_path):
            self._display_single_image(self.lbl_img_stage1, img_path)

    def _display_single_image(self, target_label, img_source):
        try:
            if isinstance(img_source, str):
                pil_img = Image.open(img_source)
            elif isinstance(img_source, np.ndarray):
                rgb = cv2.cvtColor(img_source, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb)
            elif isinstance(img_source, Image.Image):
                pil_img = img_source
            else:
                return

            max_w, max_h = 360, 210
            pil_img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(pil_img)
            target_label.config(image=tk_img, text="")
            target_label.image = tk_img
        except Exception as e:
            self.log(f"Lỗi hiển thị ảnh: {e}")

    def browse_custom_image(self):
        file_path = filedialog.askopenfilename(
            title="Chọn ảnh tấm pin quang điện thực nghiệm",
            filetypes=[("Hình ảnh", "*.jpg *.jpeg *.png *.bmp")]
        )
        if file_path:
            self.snapshot_var.set(os.path.basename(file_path))
            self._display_single_image(self.lbl_img_stage1, file_path)
            self.custom_img_path = file_path
            self.log(f"Đã chọn ảnh ngoài: {file_path}")

    def load_models_if_needed(self, device, half_precision):
        if self.model_seg is not None and self.loaded_device == device and self.loaded_half == half_precision:
            return True

        self.log(f"Đang nạp mô hình AI lên thiết bị {device.upper()} (FP16: {half_precision})...")
        seg_path = os.path.join(MODELS_DIR, "panel 2.pt")
        det_path = os.path.join(MODELS_DIR, "Solar.pt")

        if not os.path.exists(seg_path):
            self.log(f"Lỗi: Không tìm thấy tệp {seg_path}")
            return False
        if not os.path.exists(det_path):
            self.log(f"Lỗi: Không tìm thấy tệp {det_path}")
            return False

        try:
            self.model_seg = YOLO(seg_path)
            self.model_seg.to(device)

            self.model_det = YOLO(det_path)
            self.model_det.to(device)

            self.model_eff = EfficientNetB0Wrapper(device=device, half_precision=half_precision)

            self.loaded_device = device
            self.loaded_half = half_precision
            self.log(f"Đã nạp thành công toàn bộ mô hình AI trên {device.upper()}.")
            return True
        except Exception as e:
            self.log(f"Lỗi khởi tạo mô hình: {e}")
            return False

    def infer_multi_stage_pipeline(self, img_bgr, device="cpu", half=False, dirt_thresh=0.30):
        is_cuda = device.startswith("cuda") and torch.cuda.is_available()
        vis_stage1 = img_bgr.copy()

        # ==================== 1. YOLOv8-Seg (Phân đoạn & Nắn góc) ====================
        if is_cuda:
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        
        seg_res = self.model_seg(img_bgr, verbose=False, device=device, half=half)[0]
        
        corners = None
        cnt = None
        if seg_res.masks is not None and len(seg_res.masks.data) > 0:
            mask_np = (seg_res.masks.data[0].cpu().numpy() * 255).astype(np.uint8)
            mask_resized = cv2.resize(mask_np, (img_bgr.shape[1], img_bgr.shape[0]))
            corners, cnt = get_panel_corners(mask_resized)

        if corners is None:
            h, w, _ = img_bgr.shape
            corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype="float32")

        warped_img, M = warp_panel(img_bgr, corners, target_w=896, target_h=448)
        
        if is_cuda:
            torch.cuda.synchronize()
        t1 = time.perf_counter()
        t_seg = (t1 - t0) * 1000.0

        # Trực quan hóa Giai đoạn 1
        if cnt is not None:
            cv2.drawContours(vis_stage1, [cnt], -1, (0, 255, 255), 2)
        for idx_pt, pt in enumerate(corners):
            cv2.circle(vis_stage1, (int(pt[0]), int(pt[1])), 6, (0, 165, 255), -1)
            cv2.putText(vis_stage1, f"P{idx_pt+1}", (int(pt[0]) - 8, int(pt[1]) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        # ==================== 2. EfficientNet-B0 (32 Ô Lưới) ====================
        cells, coords = slice_into_32_cells(warped_img, rows=4, cols=8)
        patches_np = np.stack([c.astype(np.float32) / 255.0 for c in cells])
        patches_np = np.transpose(patches_np, (0, 3, 1, 2))
        patches_tensor = torch.tensor(patches_np, device=device)

        if is_cuda:
            torch.cuda.synchronize()
        t2 = time.perf_counter()
        
        probs = self.model_eff.predict_batch_32(patches_tensor)
        
        if is_cuda:
            torch.cuda.synchronize()
        t3 = time.perf_counter()
        t_eff = (t3 - t2) * 1000.0

        # Trực quan hóa Giai đoạn 2 (Đầu vào mạng CNN 32 ô)
        vis_stage2 = warped_img.copy()
        for (x1, y1, x2, y2) in coords:
            cv2.rectangle(vis_stage2, (x1, y1), (x2, y2), (255, 200, 0), 1)

        # ==================== 3. YOLOv8-Det (Dị Vật Cản Quang) ====================
        if is_cuda:
            torch.cuda.synchronize()
        t4 = time.perf_counter()
        
        det_res = self.model_det(img_bgr, verbose=False, device=device, half=half)[0]
        
        if is_cuda:
            torch.cuda.synchronize()
        t5 = time.perf_counter()
        t_det = (t5 - t4) * 1000.0

        t_total = t_seg + t_eff + t_det

        leaf_count = 0
        if det_res.boxes is not None:
            leaf_count = len(det_res.boxes)
            for box in det_res.boxes:
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                cls_name = self.model_det.names.get(cls_id, "Obstacle")
                cv2.rectangle(vis_stage1, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), (0, 69, 255), 2)
                cv2.putText(vis_stage1, f"{cls_name} {conf*100:.0f}%", (xyxy[0], max(xyxy[1]-4, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 69, 255), 1)

        # Trực quan hóa Giai đoạn 3 (Bản đồ 32 ô phân loại)
        vis_stage3, dirty_cells_count = self._render_stage3_overlay(warped_img, coords, probs, dirt_thresh)
        dirt_percentage = (dirty_cells_count / 32.0) * 100.0

        need_cleaning = (dirty_cells_count >= 2) or (leaf_count > 0)
        decision_text = "KÍCH HOẠT VỆ SINH (CLEANING TRIGGERED)" if need_cleaning else "MẶT PIN ĐẠT CHUẨN (NORMAL)"
        decision_color = "#ef4444" if need_cleaning else "#10b981"

        return {
            "t_seg": t_seg,
            "t_eff": t_eff,
            "t_det": t_det,
            "t_total": t_total,
            "fps": 1000.0 / max(t_total, 0.001),
            "dirty_cells": dirty_cells_count,
            "leaf_count": leaf_count,
            "dirt_percentage": dirt_percentage,
            "need_cleaning": need_cleaning,
            "decision_text": decision_text,
            "decision_color": decision_color,
            "vis_stage1": vis_stage1,
            "vis_stage2": vis_stage2,
            "vis_stage3": vis_stage3,
            "warped_raw": warped_img,
            "coords": coords,
            "probs": probs
        }

    def _render_stage3_overlay(self, warped_base, coords, probs, threshold):
        annotated = warped_base.copy()
        dirty_count = 0

        for idx, (x1, y1, x2, y2) in enumerate(coords):
            dirt_p = probs[idx][1] if probs.shape[1] > 1 else probs[idx][0]
            is_dirty = dirt_p >= threshold

            if is_dirty:
                dirty_count += 1
                color = (0, 0, 220)  # Đỏ
                label = f"B:{dirt_p*100:.0f}%"
            else:
                color = (0, 180, 0)  # Xanh
                label = f"S:{dirt_p*100:.0f}%"

            overlay = annotated.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
            cv2.addWeighted(overlay, 0.32, annotated, 0.68, 0, annotated)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)
            cv2.putText(annotated, label, (x1 + 6, y1 + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255), 1)

        return annotated, dirty_count

    def _recompute_and_update_display_with_threshold(self, threshold):
        res = self.last_inference_result
        if res is None:
            return

        vis3, dirty_cnt = self._render_stage3_overlay(res["warped_raw"], res["coords"], res["probs"], threshold)
        dirt_pct = (dirty_cnt / 32.0) * 100.0
        need_clean = (dirty_cnt >= 2) or (res["leaf_count"] > 0)
        dec_text = "KÍCH HOẠT VỆ SINH (CLEANING TRIGGERED)" if need_clean else "MẶT PIN ĐẠT CHUẨN (NORMAL)"
        dec_col = "#ef4444" if need_clean else "#10b981"

        self._display_single_image(self.lbl_img_stage3, vis3)
        self.card_res.config(text=f"Ô bẩn: {dirty_cnt}/32 | Dị vật: {res['leaf_count']} | Tỷ lệ: {dirt_pct:.1f}% (τ = {threshold*100:.0f}%)")
        self.card_decision.config(text=dec_text, fg=dec_col)

    def run_single_inference_thread(self):
        if self.is_running:
            return
        threading.Thread(target=self._run_single_inference, daemon=True).start()

    def _run_single_inference(self):
        self.is_running = True
        self.btn_single.config(state="disabled")
        self.btn_benchmark.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.lbl_status.config(text="Đang thực hiện suy luận đa tầng...")

        try:
            device = self.device_var.get()
            half = self.half_var.get()
            dirt_thresh = self.dirt_threshold_var.get() / 100.0

            if not self.load_models_if_needed(device, half):
                return

            if hasattr(self, 'custom_img_path') and os.path.exists(self.custom_img_path):
                img_path = self.custom_img_path
            else:
                sel_name = self.snapshot_var.get()
                img_path = os.path.join(SNAPSHOTS_DIR, sel_name)

            if not os.path.exists(img_path):
                self.log(f"Lỗi: Không tìm thấy ảnh: {img_path}")
                return

            img_bgr = cv2.imread(img_path)
            res = self.infer_multi_stage_pipeline(img_bgr, device=device, half=half, dirt_thresh=dirt_thresh)
            self.last_inference_result = res

            # Cập nhật 3 ảnh trực quan
            self._display_single_image(self.lbl_img_stage1, res["vis_stage1"])
            self._display_single_image(self.lbl_img_stage2, res["vis_stage2"])
            self._display_single_image(self.lbl_img_stage3, res["vis_stage3"])

            # Cập nhật các thẻ đo lường
            self.card_seg.config(text=f"{res['t_seg']:.2f} ms")
            self.card_eff.config(text=f"{res['t_eff']:.2f} ms")
            self.card_det.config(text=f"{res['t_det']:.2f} ms")
            self.card_tot.config(text=f"{res['t_total']:.2f} ms  ({res['fps']:.1f} FPS)")
            self.card_res.config(text=f"Ô bẩn: {res['dirty_cells']}/32 | Dị vật: {res['leaf_count']} | Tỷ lệ: {res['dirt_percentage']:.1f}% (τ = {dirt_thresh*100:.0f}%)")
            self.card_decision.config(text=res["decision_text"], fg=res["decision_color"])

            self.log(f"Suy luận [{os.path.basename(img_path)}]: Seg={res['t_seg']:.1f}ms | Eff={res['t_eff']:.1f}ms | Det={res['t_det']:.1f}ms | Tổng={res['t_total']:.1f}ms ({res['fps']:.1f} FPS) | Ô bẩn: {res['dirty_cells']}/32 (τ={dirt_thresh*100:.0f}%) -> {res['decision_text']}")
            self.lbl_status.config(text="Hoàn thành suy luận trực quan đa tầng.")
        except Exception as e:
            self.log(f"Lỗi suy luận: {e}")
            self.lbl_status.config(text="Có lỗi xảy ra trong quá trình thực thi.")
        finally:
            self.is_running = False
            self.btn_single.config(state="normal")
            self.btn_benchmark.config(state="normal")
            self.btn_stop.config(state="disabled")

    def run_benchmark_thread(self):
        if self.is_running:
            return
        threading.Thread(target=self._run_benchmark, daemon=True).start()

    def _run_benchmark(self):
        self.is_running = True
        self.stop_requested = False
        self.btn_single.config(state="disabled")
        self.btn_benchmark.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.progress_var.set(0)

        for item in self.tree.get_children():
            self.tree.delete(item)
        self.benchmark_records.clear()

        try:
            device = self.device_var.get()
            half = self.half_var.get()
            runs = self.runs_var.get()
            warmup = self.warm_var.get()
            dirt_thresh = self.dirt_threshold_var.get() / 100.0

            self.log("\n" + "=" * 75)
            self.log(f"BẮT ĐẦU ĐO ĐẠC ĐỘ TRỄ HỌC THUẬT: {runs} CHU KỲ | {warmup} WARM-UP | {device.upper()} (FP16: {half}) | NGƯỠNG τ: {dirt_thresh*100:.0f}%")
            self.log("=" * 75)

            if not self.load_models_if_needed(device, half):
                return

            snapshots = sorted(glob.glob(os.path.join(SNAPSHOTS_DIR, "*.jpg")) + glob.glob(os.path.join(SNAPSHOTS_DIR, "*.png")))
            if not snapshots:
                self.log("Lỗi: Không tìm thấy ảnh trong snapshots_mau.")
                return

            # Warmup Phase
            self.lbl_status.config(text=f"Đang Warm-up ({warmup} chu kỳ)...")
            self.log(f"Warm-up phần cứng ({warmup} chu kỳ để ổn định Clock Rate & Bộ đệm CUDA)...")
            warmup_img = cv2.imread(snapshots[0])
            for w_idx in range(warmup):
                if self.stop_requested:
                    self.log("Đã dừng theo yêu cầu người dùng.")
                    return
                _ = self.infer_multi_stage_pipeline(warmup_img, device=device, half=half, dirt_thresh=dirt_thresh)
            self.log("Hoàn thành Warm-up. Bắt đầu đo lặp thực nghiệm chính thức.")

            # Benchmark Phase
            seg_list, eff_list, det_list, total_list = [], [], [], []

            for run_idx in range(runs):
                if self.stop_requested:
                    self.log("Đã dừng tiến trình đo.")
                    break

                img_path = snapshots[run_idx % len(snapshots)]
                img_name = os.path.basename(img_path)
                img_bgr = cv2.imread(img_path)

                res = self.infer_multi_stage_pipeline(img_bgr, device=device, half=half, dirt_thresh=dirt_thresh)
                self.last_inference_result = res

                seg_list.append(res["t_seg"])
                eff_list.append(res["t_eff"])
                det_list.append(res["t_det"])
                total_list.append(res["t_total"])

                record = {
                    "idx": run_idx + 1,
                    "filename": img_name,
                    "seg_lat": res["t_seg"],
                    "eff_lat": res["t_eff"],
                    "det_lat": res["t_det"],
                    "total_lat": res["t_total"],
                    "fps": res["fps"],
                    "dirty_cells": res["dirty_cells"],
                    "leaf_cnt": res["leaf_count"],
                    "dirty_pct": res["dirt_percentage"],
                    "decision": res["decision_text"]
                }
                self.benchmark_records.append(record)

                self.tree.insert("", "end", values=(
                    record["idx"],
                    record["filename"],
                    f"{record['seg_lat']:.2f}",
                    f"{record['eff_lat']:.2f}",
                    f"{record['det_lat']:.2f}",
                    f"{record['total_lat']:.2f}",
                    f"{record['fps']:.1f}",
                    f"{record['dirty_cells']}/32",
                    record["leaf_cnt"],
                    f"{record['dirty_pct']:.1f}%",
                    "KÍCH HOẠT" if res["need_cleaning"] else "CHUẨN"
                ))
                self.tree.yview_moveto(1.0)

                self.card_seg.config(text=f"{res['t_seg']:.2f} ms")
                self.card_eff.config(text=f"{res['t_eff']:.2f} ms")
                self.card_det.config(text=f"{res['t_det']:.2f} ms")
                self.card_tot.config(text=f"{res['t_total']:.2f} ms  ({res['fps']:.1f} FPS)")
                self.card_res.config(text=f"Ô bẩn: {res['dirty_cells']}/32 | Dị vật: {res['leaf_count']} | Tỷ lệ: {res['dirt_percentage']:.1f}% (τ = {dirt_thresh*100:.0f}%)")
                self.card_decision.config(text=res["decision_text"], fg=res["decision_color"])

                if run_idx % 2 == 0 or run_idx == runs - 1:
                    self._display_single_image(self.lbl_img_stage1, res["vis_stage1"])
                    self._display_single_image(self.lbl_img_stage2, res["vis_stage2"])
                    self._display_single_image(self.lbl_img_stage3, res["vis_stage3"])

                pct = ((run_idx + 1) / runs) * 100.0
                self.progress_var.set(pct)
                self.lbl_status.config(text=f"Mẫu {run_idx + 1}/{runs} ({pct:.0f}%) | Độ trễ: {res['t_total']:.1f} ms | {res['decision_text']}")

            if len(total_list) > 0:
                self._compute_and_log_statistics(seg_list, eff_list, det_list, total_list, device, half, dirt_thresh)
                self.lbl_status.config(text="Hoàn thành đo lường thực nghiệm.")
                messagebox.showinfo("Hoàn Tất", f"Đã hoàn thành đo lường {len(total_list)} chu kỳ với ngưỡng τ = {dirt_thresh*100:.0f}%!\nXem chi tiết tại tab 'Bảng Thống Kê Học Thuật'.")
        except Exception as e:
            self.log(f"Lỗi đo lường: {e}")
            self.lbl_status.config(text="Có lỗi xảy ra.")
        finally:
            self.is_running = False
            self.btn_single.config(state="normal")
            self.btn_benchmark.config(state="normal")
            self.btn_stop.config(state="disabled")

    def _compute_and_log_statistics(self, seg_l, eff_l, det_l, tot_l, device, half, thresh):
        seg_np, eff_np, det_np, tot_np = np.array(seg_l), np.array(eff_l), np.array(det_l), np.array(tot_l)

        self.log("\n" + "=" * 78)
        self.log("BẢNG TỔNG HỢP KẾT QUẢ ĐỘ TRỄ SUY LUẬN HỌC THUẬT (IEEE / TNU JST)")
        self.log("=" * 78)
        self.log(f"Phần cứng thực thi: {self.hw['gpu_name']} | Thiết bị: {device.upper()} | Chế độ: {'FP16 Half' if half else 'FP32 Full'}")
        self.log(f"Số mẫu đo lặp: N = {len(tot_np)} | Ngưỡng quyết định bẩn (Tau): {thresh*100:.0f}%")
        self.log("-" * 78)
        self.log(f"1. Phân đoạn & Nắn góc (YOLOv8-Seg):  {np.mean(seg_np):6.2f} ± {np.std(seg_np):4.2f} ms  [Min: {np.min(seg_np):.2f}, Max: {np.max(seg_np):.2f}, P95: {np.percentile(seg_np, 95):.2f}]")
        self.log(f"2. Phân loại 32 ô lưới (EfficientNet-B0): {np.mean(eff_np):6.2f} ± {np.std(eff_np):4.2f} ms  [Min: {np.min(eff_np):.2f}, Max: {np.max(eff_np):.2f}, P95: {np.percentile(eff_np, 95):.2f}]")
        self.log(f"3. Phát hiện vật thể cản quang (YOLOv8-Det): {np.mean(det_np):6.2f} ± {np.std(det_np):4.2f} ms  [Min: {np.min(det_np):.2f}, Max: {np.max(det_np):.2f}, P95: {np.percentile(det_np, 95):.2f}]")
        self.log("-" * 78)
        mean_tot = np.mean(tot_np)
        fps_equiv = 1000.0 / mean_tot if mean_tot > 0 else 0
        self.log(f"TỔNG ĐỘ TRỄ SUY LUẬN TOÀN TRÌNH (E2E):  {mean_tot:6.2f} ± {np.std(tot_np):4.2f} ms  (Tốc độ: {fps_equiv:.1f} FPS)")
        self.log(f"   (Khoảng tin cậy 95%: {np.percentile(tot_np, 5):.2f} ms -> {np.percentile(tot_np, 95):.2f} ms)")
        self.log("=" * 78 + "\n")

    def save_figure_for_paper(self):
        """Xuất ảnh ghép 3 khung + Thẻ thông số chuẩn 300 DPI để chèn trực tiếp vào bài báo"""
        if self.last_inference_result is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng thực hiện 'Suy Luận 1 Ảnh' trước khi xuất ảnh minh chứng.")
            return

        res = self.last_inference_result
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(RESULTS_DIR, f"Hinh5_MinhChung_AI_{timestamp}.png")

        # Tạo ảnh tổng hợp chất lượng cao (3 Sub-figures + 1 Status Box)
        img1 = cv2.resize(res["vis_stage1"], (640, 480))
        img2 = cv2.resize(res["vis_stage2"], (640, 480))
        img3 = cv2.resize(res["vis_stage3"], (640, 480))

        # Tiêu đề học thuật
        cv2.rectangle(img1, (0, 0), (640, 40), (20, 20, 20), -1)
        cv2.putText(img1, "(a) Original & Segmentation (YOLOv8-Seg)", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        cv2.rectangle(img2, (0, 0), (640, 40), (20, 20, 20), -1)
        cv2.putText(img2, "(b) Perspective Warped ROI (CNN Input)", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        cv2.rectangle(img3, (0, 0), (640, 40), (20, 20, 20), -1)
        cv2.putText(img3, "(c) 32-Cell Soiling Map (EfficientNet-B0)", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # Panel 4: Thông số khoa học
        info_panel = np.ones((480, 640, 3), dtype=np.uint8) * 30
        cv2.rectangle(info_panel, (10, 10), (630, 470), (60, 60, 60), 2)
        cv2.putText(info_panel, "(d) Latency Breakdown & Decision", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (56, 189, 248), 2)
        
        cv2.putText(info_panel, f"1. YOLOv8-Seg (Warp):     {res['t_seg']:6.2f} ms", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)
        cv2.putText(info_panel, f"2. EfficientNet-B0 (32):   {res['t_eff']:6.2f} ms", (30, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (192, 132, 252), 2)
        cv2.putText(info_panel, f"3. YOLOv8-Det (Leaves):    {res['t_det']:6.2f} ms", (30, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (251, 191, 36), 2)
        
        cv2.line(info_panel, (30, 220), (610, 220), (100, 100, 100), 1)
        cv2.putText(info_panel, f"E2E Latency:  {res['t_total']:6.2f} ms ({res['fps']:.1f} FPS)", (30, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (52, 211, 153), 2)
        
        dirt_thresh = self.dirt_threshold_var.get()
        cv2.putText(info_panel, f"Soiled Cells: {res['dirty_cells']}/32 ({res['dirt_percentage']:.1f}%) [Threshold: {dirt_thresh:.0f}%]", (30, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (248, 113, 113), 2)
        cv2.putText(info_panel, f"Obstacles Detected: {res['leaf_count']} leaf items", (30, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (251, 191, 36), 2)
        
        dec_color = (0, 0, 255) if res["need_cleaning"] else (0, 255, 0)
        cv2.putText(info_panel, f"Action: {res['decision_text']}", (30, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.65, dec_color, 2)

        # Ghép thành ma trận 2x2
        top_row = np.hstack([img1, img2])
        bot_row = np.hstack([img3, info_panel])
        composite = np.vstack([top_row, bot_row])

        cv2.imwrite(out_path, composite)
        self.log(f"Đã xuất ảnh minh chứng độ phân giải cao cho bài báo: {out_path}")
        messagebox.showinfo("Đã Xuất Ảnh", f"Đã xuất ảnh minh chứng chất lượng cao (2x2 Composite):\n{out_path}\n\nBạn có thể chèn trực tiếp ảnh này vào bài báo Word/LaTeX.")

    def stop_process(self):
        self.stop_requested = True
        self.lbl_status.config(text="Đang dừng tiến trình...")

    def export_report(self):
        if not self.benchmark_records:
            messagebox.showwarning("Cảnh báo", "Chưa có dữ liệu đo đạc nào để xuất báo cáo. Vui lòng chạy đo lường trước.")
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_filename = os.path.join(RESULTS_DIR, f"bao_cao_do_tre_ai_{timestamp}.csv")
        txt_filename = os.path.join(RESULTS_DIR, f"bao_cao_do_tre_ai_{timestamp}.txt")

        try:
            with open(csv_filename, mode='w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=list(self.benchmark_records[0].keys()))
                writer.writeheader()
                writer.writerows(self.benchmark_records)

            with open(txt_filename, mode='w', encoding='utf-8') as f:
                f.write(self.txt_log.get("1.0", tk.END))

            messagebox.showinfo("Xuất Báo Cáo", f"Đã lưu báo cáo thực nghiệm:\n- CSV: {csv_filename}\n- TXT: {txt_filename}")
            self.log(f"Đã lưu báo cáo thực nghiệm: {csv_filename}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể ghi tệp: {e}")

    def open_results_folder(self):
        try:
            os.startfile(RESULTS_DIR)
        except Exception as e:
            messagebox.showinfo("Thư mục kết quả", f"Đường dẫn kết quả: {RESULTS_DIR}")


def main():
    root = tk.Tk()
    app = LatencyBenchmarkGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
