"""
AI Assistant Module cho Hệ Thống Vệ Sinh Tấm Pin Mặt Trời (SolarClean)
======================================================================
Mô hình AI: Hardcoded `qwen2.5:0.5b` (Siêu nhẹ, ~390MB, chạy mượt trên máy yếu).
Tính năng:
  - Tự động lấy dữ liệu vận hành thực tế (bụi bẩn, PLC, công suất PZEM, số lần rửa) đưa vào Prompt.
  - Tự động phân tích ý định ra lệnh (Kích hoạt vệ sinh, Khởi động, Dừng hệ thống, Kết nối PLC).
  - Kết nối Ollama API local (http://localhost:11434).
"""

import json
import re
import requests
import threading
import time
from typing import Dict, Any, Tuple, Optional, Generator

OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "solar-ai"
FALLBACK_MODEL = "qwen2.5:0.5b"


class AIAssistant:
    def __init__(self, host: str = OLLAMA_HOST, model: str = DEFAULT_MODEL):
        self.host = host.rstrip('/')
        self.model = model
        self.is_pulling = False

    def check_ollama(self) -> Tuple[bool, str]:
        """Kiểm tra dịch vụ Ollama local."""
        try:
            res = requests.get(f"{self.host}/api/tags", timeout=3)
            if res.status_code == 200:
                return True, "Ollama đang hoạt động bình thường"
            return False, f"Server phản hồi lỗi: {res.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Không thể kết nối Ollama local (localhost:11434). Vui lòng chạy 'ollama serve'."
        except Exception as e:
            return False, f"Lỗi kết nối: {str(e)}"

    def get_installed_models(self) -> list:
        """Danh sách các model đã cài trong Ollama."""
        try:
            res = requests.get(f"{self.host}/api/tags", timeout=3)
            if res.status_code == 200:
                data = res.json()
                return [m.get('name', '') for m in data.get('models', []) if m.get('name')]
        except Exception:
            pass
        return []

    def get_active_model(self) -> str:
        """Lấy tên model thực tế đang có sẵn trong Ollama."""
        models = self.get_installed_models()
        if any(self.model in m for m in models):
            return self.model
        if any("solar-ai" in m for m in models):
            return "solar-ai"
        if any("qwen2.5:0.5b" in m for m in models):
            return "qwen2.5:0.5b"
        if any("qwen2.5:7b" in m for m in models):
            return "qwen2.5:7b"
        return self.model

    def ensure_model_async(self):
        """Đảm bảo model có sẵn."""
        pass



    def build_system_context(self, current_results: Dict[str, Any]) -> str:
        """Tạo đoạn thông tin bối cảnh thời gian thực & Tri thức hệ thống cho AI."""
        p_dirty = current_results.get('p_dirty', 0.0) * 100 if current_results else 0.0
        area_ratio = current_results.get('area_ratio', 0.0) * 100 if current_results else 0.0
        label_name = current_results.get('label_name', 'Chưa rõ') if current_results else 'Chưa rõ'
        status = current_results.get('status', 'Đang khởi tạo') if current_results else 'Chưa chạy'
        is_running = current_results.get('is_running', False) if current_results else False
        clean_count = current_results.get('clean_count', 0) if current_results else 0
        
        plc_connected = current_results.get('plc_connected', False) if current_results else False
        plc_status = current_results.get('plc_status', 'Không kết nối') if current_results else 'Chưa kết nối'
        plc_ip = current_results.get('plc_ip', '192.168.1.1') if current_results else '192.168.1.1'

        voltage = current_results.get('power_voltage', 0) if current_results else 0
        current_amp = current_results.get('power_current', 0) if current_results else 0
        power_watts = current_results.get('power_watts', 0) if current_results else 0
        energy_kwh = current_results.get('power_energy', 0) if current_results else 0

        context = (
            "BẠN LÀ TRỢ LÝ AI THÔNG MINH CHO HỆ THỐNG VỆ SINH TẤM PIN MẶT TRỜI (SOLAR CLEAN).\n"
            "DỮ LIỆU THỜI GIAN THỰC CỦA TRẠM PIN:\n"
            f"- Giám sát: {'Đang hoạt động' if is_running else 'Đang tạm dừng'}\n"
            f"- Trạng thái bề mặt: {status} (Nhãn AI: {label_name})\n"
            f"- Tỷ lệ bẩn: {area_ratio:.1f}%\n"
            f"- Số lần đã rửa: {clean_count} lần\n"
            f"- Kết nối PLC (IP {plc_ip}): {'Đã kết nối' if plc_connected else 'Chưa kết nối'}\n"
            f"- Cảm biến công suất PZEM-017: {voltage}V, {current_amp}A, {power_watts}W, {energy_kwh}kWh.\n"
            "\n"
            "QUY TẮC PHẢN HỒI:\n"
            "1. Luôn trả lời đầy đủ câu, tự nhiên và chính xác bằng tiếng Việt.\n"
            "2. Nếu người dùng hỏi kiến thức chung hoặc toán học: Trả lời đúng trọng tâm và hoàn chỉnh câu.\n"
            "3. Nếu hỏi về trạm pin: Dùng dữ liệu thời gian thực trên để giải thích rõ ràng.\n"
            "4. Tuyệt đối không dừng câu giữa chừng."
        )
        return context




    def detect_and_execute_intent(self, user_message: str, command_queue: Any, current_results: Dict[str, Any]) -> Optional[str]:
        """
        Phân tích câu nói/tin nhắn của người dùng và kích hoạt lệnh thực thi hoặc thay đổi tham số hệ thống qua command_queue.
        Trả về chuỗi thông báo thực thi lệnh (nếu có).
        """
        msg_lower = user_message.lower().strip()
        executed_action = None

        # 1. Lệnh Kích hoạt vệ sinh
        clean_keywords = [
            "vệ sinh", "rửa pin", "làm sạch", "rửa tấm pin", "lau pin", "kích hoạt vệ sinh", 
            "clean", "rửa pin giúp", "rửa giùm", "xịt nước", "chổi xoay", "cho rửa pin", "vệ sinh giúp"
        ]
        if any(kw in msg_lower for kw in clean_keywords) and ("không" not in msg_lower and "đừng" not in msg_lower and "ngưỡng" not in msg_lower):
            if command_queue is not None:
                command_queue.put(('manual_clean', True))
                executed_action = "🧹 [Hệ thống]: Đã phát lệnh KÍCH HOẠT VỆ SINH TẤM PIN tới PLC thành công!"

        # 2. Lệnh Khởi động / Mở hệ thống
        start_keywords = [
            "khởi động", "bắt đầu giám sát", "bật hệ thống", "chạy hệ thống", "start system", 
            "mở giám sát", "mở hệ thống", "mở máy", "bật máy", "bật lên", "mở lên", "chạy máy", 
            "mở chạy", "kích hoạt hệ thống", "bật giám sát", "mở giúp", "bật giúp", "start"
        ]
        if any(kw in msg_lower for kw in start_keywords) and ("không" not in msg_lower and "đừng" not in msg_lower):
            if command_queue is not None:
                command_queue.put(('system_start', True))
                executed_action = "▶️ [Hệ thống]: Đã phát lệnh KHỞI ĐỘNG GIÁM SÁT HỆ THỐNG thành công!"

        # 3. Lệnh Dừng / Tắt hệ thống
        stop_keywords = [
            "dừng hệ thống", "tắt hệ thống", "ngưng hệ thống", "tắt giám sát", "stop system", 
            "dừng lại", "tắt máy", "dừng máy", "tắt đi", "tắt giúp", "ngắt hệ thống", "dừng giúp", "stop"
        ]
        if any(kw in msg_lower for kw in stop_keywords):
            if command_queue is not None:
                command_queue.put(('system_stop', True))
                executed_action = "⏹️ [Hệ thống]: Đã phát lệnh DỪNG GIÁM SÁT HỆ THỐNG thành công!"

        # 4. Lệnh Kết nối lại PLC
        plc_keywords = ["kết nối plc", "kết nối lại plc", "reconnect plc", "nối lại plc"]
        if any(kw in msg_lower for kw in plc_keywords) and "ip" not in msg_lower:
            if command_queue is not None:
                plc_ip = current_results.get('plc_ip', '192.168.1.1') if current_results else '192.168.1.1'
                command_queue.put(('plc_reconnect', plc_ip))
                executed_action = f"🔌 [Hệ thống]: Đã phát lệnh KẾT NỐI LẠI PLC tại địa chỉ IP {plc_ip}!"


        # 5. THAY ĐỔI THỜI GIAN CHU KỲ (SNAPSHOT INTERVAL)
        interval_match = re.search(r'(?:chu kỳ|snapshot|interval|thời gian chụp|chu kỳ chụp|chụp ảnh)\D*?(\d+)\s*(phút|phut|m|giây|giay|s)?', msg_lower)
        if interval_match:
            val = int(interval_match.group(1))
            unit = interval_match.group(2) or ''
            if 'giây' in unit or 'giay' in unit or unit == 's':
                seconds = val
            else:
                seconds = val * 60 if val < 120 else val

            if 60 <= seconds <= 86400:
                if command_queue is not None:
                    command_queue.put(('snapshot_interval', seconds))
                    executed_action = f"⏱️ [Hệ thống]: Đã đặt thời gian chu kỳ chụp ảnh thành {seconds // 60} phút ({seconds} giây)!"

        # 6. THAY ĐỔI NGƯỠNG DIỆN TÍCH BẨN (DIRT AREA THRESHOLD)
        dirt_match = re.search(r'(?:ngưỡng bẩn|ngưỡng diện tích|dirt threshold|ngưỡng vết bẩn|diện tích bẩn)\D*?(\d+(?:\.\d+)?)\s*(%)?', msg_lower)
        if dirt_match:
            val_float = float(dirt_match.group(1))
            has_pct = dirt_match.group(2) == '%'
            if val_float > 1.0 or has_pct:
                threshold = val_float / 100.0
            else:
                threshold = val_float

            if 0.01 <= threshold <= 0.95:
                if command_queue is not None:
                    command_queue.put(('threshold', threshold))
                    executed_action = f"🎯 [Hệ thống]: Đã thay đổi ngưỡng diện tích bẩn thành {threshold * 100:.1f}%!"

        # 7. THAY ĐỔI NGƯỠNG CNN (CNN DIRTY THRESHOLD)
        cnn_match = re.search(r'(?:ngưỡng cnn|cnn threshold|độ tự tin cnn)\D*?(\d+(?:\.\d+)?)\s*(%)?', msg_lower)
        if cnn_match:
            val_float = float(cnn_match.group(1))
            has_pct = cnn_match.group(2) == '%'
            if val_float > 1.0 or has_pct:
                cnn_threshold = val_float / 100.0
            else:
                cnn_threshold = val_float

            if 0.10 <= cnn_threshold <= 0.99:
                if command_queue is not None:
                    command_queue.put(('cnn_dirty_threshold', cnn_threshold))
                    executed_action = f"🧠 [Hệ thống]: Đã thay đổi ngưỡng CNN thành {cnn_threshold * 100:.0f}%!"

        # 8. THAY ĐỔI CẤU HÌNH IP PLC
        ip_match = re.search(r'(?:ip plc|đổi ip|đặt ip)\D*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', msg_lower)
        if ip_match:
            new_ip = ip_match.group(1)
            if command_queue is not None:
                command_queue.put(('plc_ip_update', new_ip))
                executed_action = f"🔌 [Hệ thống]: Đã cập nhật địa chỉ IP PLC thành {new_ip}!"

        # 9. THAY ĐỔI CAMERA ID
        cam_match = re.search(r'(?:đổi camera|chọn camera|camera id)\D*?(\d+)', msg_lower)
        if cam_match:
            cam_id = int(cam_match.group(1))
            if command_queue is not None:
                command_queue.put(('camera', cam_id))
                executed_action = f"📷 [Hệ thống]: Đã chuyển sang Camera ID {cam_id}!"

        return executed_action


    def check_math_and_general_questions(self, user_message: str) -> Optional[str]:
        """Tự động nhận diện và tính toán các phép toán cơ bản bằng chữ tiếng Việt và ký hiệu số học."""
        msg_lower = user_message.lower().strip()

        word_to_num = {
            "không": 0, "khong": 0, "một": 1, "mot": 1, "hai": 2, "ba": 3,
            "bốn": 4, "bon": 4, "tư": 4, "năm": 5, "nam": 5, "sáu": 6, "sau": 6,
            "bảy": 7, "bay": 7, "tám": 8, "tam": 8, "chín": 9, "chin": 9, "mười": 10, "muoi": 10
        }

        text_math_pattern = r'^\s*(không|khong|một|mot|hai|ba|bốn|bon|tư|năm|nam|sáu|sau|bảy|bay|tám|tam|chín|chin|mười|muoi|\d+)\s*(cộng|cong|\+|\-|trừ|tru|nhân|nhan|\*|chia|\/)\s*(không|khong|một|mot|hai|ba|bốn|bon|tư|năm|nam|sáu|sau|bảy|bay|tám|tam|chín|chin|mười|muoi|\d+)'
        match = re.search(text_math_pattern, msg_lower)
        if match:
            n1_str, op, n2_str = match.group(1), match.group(2), match.group(3)
            n1 = word_to_num[n1_str] if n1_str in word_to_num else (float(n1_str) if '.' in n1_str else int(n1_str))
            n2 = word_to_num[n2_str] if n2_str in word_to_num else (float(n2_str) if '.' in n2_str else int(n2_str))

            if op in ['cộng', 'cong', '+']:
                res = n1 + n2
                return f"{n1} + {n2} = {res}."
            elif op in ['trừ', 'tru', '-']:
                res = n1 - n2
                return f"{n1} - {n2} = {res}."
            elif op in ['nhân', 'nhan', '*']:
                res = n1 * n2
                return f"{n1} x {n2} = {res}."
            elif op in ['chia', '/']:
                if n2 != 0:
                    res = n1 / n2
                    res_str = f"{res:.2f}".rstrip('0').rstrip('.') if isinstance(res, float) else str(res)
                    return f"{n1} : {n2} = {res_str}."
                return "Không thể chia cho 0."

        return None

    def check_security_guardrails(self, user_message: str) -> Optional[str]:
        """Bộ lọc bảo mật chủ động chặn các câu hỏi cố tình khai thác thông tin model hoặc mật khẩu."""
        msg_lower = user_message.lower().strip()

        # Hỏi về model / tên mô hình / thuật toán AI
        model_privacy_keywords = [
            "model gì", "dùng model", "tên model", "mô hình gì", "mô hình tên",
            "dùng qwen", "dùng ollama", "dùng llama", "gpt gì", "bạn là gpt",
            "mô hình nào", "model nào", "dùng ai gì", "thuật toán ai gì"
        ]
        if any(kw in msg_lower for kw in model_privacy_keywords):
            return "Tôi là Trợ lý AI Smart Solar giám sát hệ thống vệ sinh tấm pin mặt trời."

        # Hỏi về mật khẩu / secret key / credentials
        credential_keywords = [
            "mật khẩu", "password", "pass admin", "secret key", "tài khoản admin",
            "xin pass", "cho xin mật khẩu", "hash password", "token admin"
        ]
        if any(kw in msg_lower for kw in credential_keywords):
            return "Thông tin bảo mật và tài khoản hệ thống được bảo vệ an toàn. Tôi không được phép cung cấp thông tin này."

        return None

    def chat(self, user_message: str, current_results: Dict[str, Any], command_queue: Any = None) -> Dict[str, Any]:
        """
        Xử lý tin nhắn từ người dùng:
        1. Kiểm tra Phép toán cơ bản (tính 0ms cho model nhẹ).
        2. Kiểm tra Guardrail bảo mật (chặn tiết lộ model/mật khẩu).
        3. Phân tích ý định RA LỆNH -> Thực thi ngay qua command_queue & thông báo 1 câu.
        4. HỎI ĐÁP -> Gọi Ollama LLM trả lời tự nhiên, ngắn gọn, đúng trọng tâm.
        """
        # 1. Phép toán nhanh
        math_reply = self.check_math_and_general_questions(user_message)
        if math_reply:
            return {"reply": math_reply, "action": None, "model": "hidden"}

        # 2. Kiểm tra Guardrail bảo mật
        security_reply = self.check_security_guardrails(user_message)
        if security_reply:
            return {"reply": security_reply, "action": None, "model": "hidden"}


        # 2. Phân tích & thực thi lệnh hệ thống (RA LỆNH)
        executed_action = self.detect_and_execute_intent(user_message, command_queue, current_results)
        if executed_action:
            reply_text = f"{executed_action} Tôi có thể giúp gì tiếp theo cho bạn?"
            return {
                "reply": reply_text,
                "action": executed_action,
                "model": "hidden"
            }

        # 3. HỎI ĐÁP (MODEL OLLAMA SUY LUẬN TỰ NHIÊN): Gọi LLM
        is_online, status_msg = self.check_ollama()
        if not is_online:
            resp_text = (
                f"⚠️ Không thể kết nối với dịch vụ AI Trực tuyến.\n"
                f"Chi tiết: {status_msg}\n\n"
                f"Vui lòng đảm bảo dịch vụ AI local đã được khởi động."
            )
            return {"reply": resp_text, "action": None, "model": "hidden"}



        # Đảm bảo model nhẹ đã tải
        self.ensure_model_async()

        # Tạo System Prompt bối cảnh thực tế & quy tắc bảo mật
        system_context = self.build_system_context(current_results)
        active_model = self.get_active_model()
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": system_context},
                {"role": "user", "content": user_message}
            ],

            "stream": False,

            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "repeat_penalty": 1.2,
                "num_predict": 512,  # Tăng lên 512 token để câu trả lời hoàn chỉnh, không bị ngắt giữa chừng
                "num_gpu": 0
            }
        }



        try:
            res = requests.post(f"{self.host}/api/chat", json=payload, timeout=30)
            if res.status_code == 200:
                data = res.json()
                ai_reply = data.get("message", {}).get("content", "").strip()
                if not ai_reply:
                    ai_reply = "Tôi đã ghi nhận câu hỏi của bạn."
            else:
                ai_reply = f"Hệ thống bận ({res.status_code}). Vui lòng thử lại sau."
        except Exception as e:
            ai_reply = f"Không thể kết nối với trợ lý AI: {str(e)}"

        if executed_action:
            ai_reply = f"{executed_action}\n\n{ai_reply}"

        return {
            "reply": ai_reply,
            "action": executed_action,
            "model": "hidden"
        }



# Global singleton instance
ai_engine = AIAssistant()



# Global singleton instance
ai_engine = AIAssistant()
