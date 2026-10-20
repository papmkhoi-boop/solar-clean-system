### Bảng: Phân rã thời gian xử lý và tài nguyên tính toán của chuỗi mô hình AI
*(Thực nghiệm trên: NVIDIA GeForce RTX 3050 Ti Laptop GPU, CPU: 16 Cores, PyTorch 2.7.1+cu118, Batch size = 1, N = 2 chu kỳ độc lập)*

| Phân đoạn xử lý | Tiền xử lý ($T_{\text{pre}}$) | Suy luận ($T_{\text{infer}}$) | Hậu xử lý ($T_{\text{post}}$) | Tổng độ trễ ($T_{\text{total}}$) |
| :--- | :---: | :---: | :---: | :---: |
| **YOLOv8-Seg** (Tách mặt pin) | 0.1 ± 0.0 ms | 59.6 ± 0.9 ms | 1.0 ± 0.0 ms | **60.5 ms** |
| **YOLOv8** (Dị vật lá cây) | — | 7.7 ± 0.0 ms | 0.7 ± 0.0 ms | **8.5 ms** |
| **Nắn thẳng & Tách 32 ô ROI** | — | — | — | **25.9 ± 0.3 ms** |
| **EfficientNet-B0** (32 ô bẩn) | — | 46.6 ± 6.8 ms | — | **46.6 ± 6.8 ms** |
| **Toàn bộ chuỗi (Pipeline)** | **0.1 ms** | **113.9 ms** | **1.7 ms** | **145.6 ± 7.9 ms** |

**Tốc độ xử lý hiệu dụng:** **6.9 FPS**
