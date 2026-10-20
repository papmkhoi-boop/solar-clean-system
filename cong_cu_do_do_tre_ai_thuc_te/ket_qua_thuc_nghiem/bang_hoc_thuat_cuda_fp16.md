### Bảng: Phân rã thời gian xử lý và tài nguyên tính toán của chuỗi mô hình AI
*(Thực nghiệm trên: NVIDIA GeForce RTX 3050 Ti Laptop GPU, CPU: 16 Cores, PyTorch 2.7.1+cu118, Batch size = 1, N = 5 chu kỳ độc lập)*

| Phân đoạn xử lý | Tiền xử lý ($T_{\text{pre}}$) | Suy luận ($T_{\text{infer}}$) | Hậu xử lý ($T_{\text{post}}$) | Tổng độ trễ ($T_{\text{total}}$) |
| :--- | :---: | :---: | :---: | :---: |
| **YOLOv8-Seg** (Tách mặt pin) | 0.2 ± 0.1 ms | 36.6 ± 7.6 ms | 0.9 ± 0.3 ms | **37.5 ms** |
| **YOLOv8** (Dị vật lá cây) | — | 9.8 ± 3.1 ms | 0.8 ± 0.2 ms | **10.6 ms** |
| **Nắn thẳng & Tách 32 ô ROI** | — | — | — | **19.0 ± 1.3 ms** |
| **EfficientNet-B0** (32 ô bẩn) | — | 26.7 ± 13.4 ms | — | **26.7 ± 13.4 ms** |
| **Toàn bộ chuỗi (Pipeline)** | **0.2 ms** | **73.0 ms** | **1.7 ms** | **97.5 ± 12.0 ms** |

**Tốc độ xử lý hiệu dụng:** **10.3 FPS**
