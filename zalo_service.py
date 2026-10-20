"""
zalo_service.py — Zalo Bot & Smart Notification Module for SolarClean
======================================================================
Tích hợp Zalo Bot (thư viện python-zalo-bot) cho hệ thống vệ sinh pin mặt trời:
  1. Cảnh báo tự động đa kênh qua Zalo (Bụi bẩn, Lá cây, Phân chim, Nứt vỡ, Hiệu suất).
  2. Chatbot 2 chiều kết nối AI Ollama (qwen2.5:0.5b) và ra lệnh điều khiển hệ thống/PLC.
  3. Lệnh nhanh: /start, /status, /clean, /power, /stop, /startsys, /help.
  4. Quản lý danh sách Chat ID nhận cảnh báo, tự động đăng ký khi người dùng nhắn tin.
  5. Cơ chế Cooldown thông minh chống spam tin nhắn.
"""

import os
import sys
import time
import json
import asyncio
import threading
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

# Fix Windows console encoding
def _configure_console_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

_configure_console_encoding()

# Resolve path
def _runtime_path(*parts):
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, *parts)

CONFIG_FILE = _runtime_path('zalo_bot_config.json')

# Import zalo_bot
try:
    import zalo_bot
    from zalo_bot import Bot, Update
    from zalo_bot.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
    from zalo_bot.constants import ChatAction
    ZALO_BOT_AVAILABLE = True
except ImportError:
    ZALO_BOT_AVAILABLE = False
    print("⚠️ python-zalo-bot chưa được cài đặt (pip install python-zalo-bot)")


# ==================== DEFAULT CONFIGURATION ====================

DEFAULT_ZALO_CONFIG = {
    "enabled": True,
    "bot_token": "3577504560494130074:mggfboWWxgQzraiWFFhZkFiwAscqdYfsdoucNqIcoUSsuNPayKUNVPLvBjXxQVPk",
    "admin_chat_ids": [],
    "alert_cooldown_seconds": 600,       # 10 phút giữa 2 cảnh báo cùng loại
    "alert_on_dirt": True,
    "alert_on_debris": True,
    "alert_on_crack": True,
    "alert_on_plc_clean": True,
    "send_snapshots": True
}


class ZaloService:
    """
    Quản lý Zalo Bot & Cảnh báo thông minh chạy nền đa luồng.
    """

    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        self.lock = threading.Lock()
        
        # Runtime states
        self.bot_app = None
        self.bot_instance: Optional[Any] = None
        self.is_running = False
        self.bot_info: Dict[str, Any] = {}
        self.bot_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Cooldown tracking: alert_key -> timestamp
        self._last_alert_times: Dict[str, float] = {}
        
        # References to system state (set by Desktop App or FastAPI)
        self.current_results_getter = None
        self.command_queue = None

    # ── Configuration Management ──

    def _load_config(self) -> Dict[str, Any]:
        """Tải cấu hình từ file JSON hoặc dùng mặc định."""
        cfg = DEFAULT_ZALO_CONFIG.copy()
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cfg.update(data)
            else:
                self._save_config(cfg)
        except Exception as e:
            print(f"⚠️ Lỗi đọc file cấu hình Zalo Bot: {e}")
        return cfg

    def _save_config(self, cfg: Optional[Dict[str, Any]] = None):
        """Lưu cấu hình ra file JSON."""
        if cfg is None:
            cfg = self.config
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ Lỗi ghi file cấu hình Zalo Bot: {e}")

    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Cập nhật cấu hình và lưu file."""
        with self.lock:
            old_token = self.config.get('bot_token')
            self.config.update(new_config)
            self._save_config()
            
            # Nếu token thay đổi hoặc bật/tắt, khởi động lại bot
            if 'bot_token' in new_config and new_config['bot_token'] != old_token:
                self.restart()
            elif 'enabled' in new_config:
                if new_config['enabled'] and not self.is_running:
                    self.start()
                elif not new_config['enabled'] and self.is_running:
                    self.stop()
        return True

    def add_chat_id(self, chat_id: str):
        """Tự động thêm Chat ID vào danh sách nhận thông báo."""
        if not chat_id:
            return
        chat_id_str = str(chat_id).strip()
        with self.lock:
            ids = self.config.get('admin_chat_ids', [])
            if chat_id_str not in ids:
                ids.append(chat_id_str)
                self.config['admin_chat_ids'] = ids
                self._save_config()
                print(f"📱 [Zalo Bot] Đã lưu Chat ID mới nhận cảnh báo: {chat_id_str}")

    def get_status(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái hoạt động của Zalo Bot."""
        return {
            "available": ZALO_BOT_AVAILABLE,
            "running": self.is_running,
            "enabled": self.config.get('enabled', True),
            "bot_name": self.bot_info.get('display_name', self.bot_info.get('account_name', 'Bot Solar Clean')),
            "bot_id": self.bot_info.get('id', 'N/A'),
            "admin_count": len(self.config.get('admin_chat_ids', [])),
            "admin_chat_ids": self.config.get('admin_chat_ids', []),
            "cooldown_seconds": self.config.get('alert_cooldown_seconds', 600)
        }

    # ── Context & Command Integration ──

    def set_system_hooks(self, results_getter, cmd_queue):
        """Gắn hàm đọc current_results và command_queue từ ứng dụng chính."""
        self.current_results_getter = results_getter
        self.command_queue = cmd_queue

    def _get_current_results(self) -> Dict[str, Any]:
        """Lấy dữ liệu thời gian thực của trạm pin."""
        if callable(self.current_results_getter):
            try:
                res = self.current_results_getter()
                if isinstance(res, dict):
                    return res
            except Exception:
                pass
        return {}

    @staticmethod
    def _extract_chat_id(update: Any) -> str:
        """Trích xuất Chat ID an toàn từ Update."""
        if not update:
            return ""
        try:
            if hasattr(update, 'message') and update.message and getattr(update.message, 'chat', None):
                return str(update.message.chat.id)
            if getattr(update, 'effective_user', None):
                return str(update.effective_user.id)
        except Exception:
            pass
        return ""

    @staticmethod
    def _extract_user_name(update: Any) -> str:
        """Trích xuất tên hiển thị của người dùng an toàn."""
        if not update:
            return "Quý khách"
        try:
            if getattr(update, 'effective_user', None):
                return getattr(update.effective_user, 'display_name', 'Quý khách')
            if hasattr(update, 'message') and update.message and getattr(update.message, 'from_user', None):
                return getattr(update.message.from_user, 'display_name', 'Quý khách')
        except Exception:
            pass
        return "Quý khách"

    # ── Bot Command Handlers ──

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /start."""
        try:
            chat_id = self._extract_chat_id(update)
            user_name = self._extract_user_name(update)
            
            # Tự động đăng ký Chat ID để nhận cảnh báo
            if chat_id:
                self.add_chat_id(chat_id)

            welcome_text = (
                f"☀️ **XIN CHÀO {user_name.upper()}!** ☀️\n"
                f"Tôi là **Trợ lý AI Smart Solar** — Giám sát & Vệ sinh Tấm Pin Mặt Trời Tự Động.\n\n"
                f"✅ **Chat ID của bạn:** `{chat_id}` (Đã đăng ký nhận cảnh báo tự động!)\n\n"
                f"📌 **CÁC LỆNH NHANH:**\n"
                f"🔹 `/status` — Xem trạng thái pin, bụi bẩn, PLC & công suất PZEM\n"
                f"🔹 `/clean` — Kích hoạt vệ sinh tấm pin ngay lập tức qua PLC\n"
                f"🔹 `/power` — Xem thông số điện áp, dòng điện, công suất\n"
                f"🔹 `/startsys` — Khởi động giám sát hệ thống\n"
                f"🔹 `/stop` — Dừng giám sát hệ thống\n"
                f"🔹 `/help` — Xem danh sách câu hỏi & lệnh mẫu\n\n"
                f"💬 **CHAT TRỰC TIẾP VỚI AI:**\n"
                f"Bạn có thể nhắn bất kỳ câu hỏi nào bằng tiếng Việt, ví dụ:\n"
                f"• *'Pin hiện tại có bị bẩn không?'*\n"
                f"• *'Rửa pin giúp tôi'* (AI sẽ tự động kích hoạt PLC)\n"
                f"• *'Công suất phát điện hiện tại là bao nhiêu?'*\n"
                f"• *'Đặt ngưỡng bẩn thành 10%'*"
            )
            await update.message.reply_text(welcome_text)
        except Exception as e:
            print(f"❌ [Zalo Bot] Lỗi /start: {e}")


    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /status."""
        try:
            cid = self._extract_chat_id(update)
            if cid: self.add_chat_id(cid)

            res = self._get_current_results()
            p_dirty = res.get('p_dirty', 0.0) * 100
            area_ratio = res.get('area_ratio', 0.0) * 100
            status_text = res.get('status', 'Đang giám sát')
            label_name = res.get('label_name', 'Chưa rõ')
            is_running = res.get('is_running', True)
            clean_count = res.get('clean_count', 0)
            
            plc_conn = res.get('plc_connected', False)
            plc_status = "ĐÃ KẾT NỐI SẴN SÀNG" if plc_conn else f"CHƯA KẾT NỐI ({res.get('plc_status', 'N/A')})"
            plc_ip = res.get('plc_ip', '192.168.1.1')

            voltage = res.get('power_voltage', 0.0)
            current_amp = res.get('power_current', 0.0)
            power_watts = res.get('power_watts', 0.0)
            energy_kwh = res.get('power_energy', 0.0)

            dirt_count = res.get('dirty_patch_count', 0)
            valid_count = res.get('valid_patch_count', 32)

            # Lỗi YOLO
            clean_faults = res.get('yolo_clean_faults', [])
            crack_faults = res.get('yolo_crack_faults', [])
            faults_str = ", ".join(clean_faults + crack_faults) if (clean_faults or crack_faults) else "Không có vật cản"

            status_msg = (
                f"📊 **BÁO CÁO TRẠNG THÁI HỆ THỐNG SOLAR**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ Thời gian: {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}\n"
                f"🖥️ Giám sát: {'🟢 ĐANG CHẠY' if is_running else '🔴 ĐANG TẮT'}\n"
                f"🔍 Đánh giá AI: **{status_text}** (Nhãn: `{label_name}`)\n"
                f"🧹 Mức độ bẩn: **{area_ratio:.1f}%** ({dirt_count}/{valid_count} ô bẩn)\n"
                f"🍂 Vật cản (YOLO): {faults_str}\n"
                f"🚿 Số lần đã rửa: **{clean_count}** lần\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔌 **PLC Siemens S7 ({plc_ip}):**\n"
                f"   • Trạng thái: {plc_status}\n"
                f"⚡ **Cảm biến công suất (PZEM-017):**\n"
                f"   • Điện áp: `{voltage:.1f} V` | Dòng: `{current_amp:.2f} A`\n"
                f"   • Công suất: `{power_watts:.1f} W`\n"
                f"   • Sản lượng: `{energy_kwh:.3f} kWh`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💡 Gõ `/clean` để kích hoạt rửa pin ngay."
            )
            await update.message.reply_text(status_msg)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi lấy trạng thái: {str(e)}")

    async def _handle_clean(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /clean (kích hoạt vệ sinh)."""
        try:
            cid = self._extract_chat_id(update)
            if cid: self.add_chat_id(cid)

            if self.command_queue is not None:
                self.command_queue.put(('manual_clean', True))
                await update.message.reply_text("🧹 **[HỆ THỐNG]: ĐÃ PHÁT LỆNH KÍCH HOẠT VỆ SINH TỚI PLC!**\nChổi xoay và vòi xịt nước đang được kích hoạt...")
            else:
                await update.message.reply_text("⚠️ Chưa kết nối với hàng đợi điều khiển của ứng dụng chính.")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi khi kích hoạt vệ sinh: {str(e)}")

    async def _handle_power(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /power."""
        try:
            cid = self._extract_chat_id(update)
            if cid: self.add_chat_id(cid)

            res = self._get_current_results()
            voltage = res.get('power_voltage', 0.0)
            current_amp = res.get('power_current', 0.0)
            power_watts = res.get('power_watts', 0.0)
            energy_kwh = res.get('power_energy', 0.0)

            power_msg = (
                f"⚡ **THÔNG SỐ ĐIỆN NĂNG (PZEM-017 Modbus RTU)**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔋 Điện áp (Voltage): **{voltage:.2f} V**\n"
                f"🔌 Dòng điện (Current): **{current_amp:.2f} A**\n"
                f"💡 Công suất tức thời: **{power_watts:.1f} W**\n"
                f"📈 Điện năng tích lũy: **{energy_kwh:.4f} kWh**\n"
                f"⏱️ Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}"
            )
            await update.message.reply_text(power_msg)
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi đọc công suất: {str(e)}")

    async def _handle_startsys(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /startsys."""
        cid = self._extract_chat_id(update)
        if cid: self.add_chat_id(cid)

        if self.command_queue is not None:
            self.command_queue.put(('system_start', True))
            await update.message.reply_text("▶️ **[HỆ THỐNG]: Đã phát lệnh KHỞI ĐỘNG GIÁM SÁT thành công!**")
        else:
            await update.message.reply_text("⚠️ Hệ thống điều khiển chưa sẵn sàng.")

    async def _handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /stop."""
        cid = self._extract_chat_id(update)
        if cid: self.add_chat_id(cid)

        if self.command_queue is not None:
            self.command_queue.put(('system_stop', True))
            await update.message.reply_text("⏹️ **[HỆ THỐNG]: Đã phát lệnh DỪNG GIÁM SÁT thành công!**")
        else:
            await update.message.reply_text("⚠️ Hệ thống điều khiển chưa sẵn sàng.")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý lệnh /help."""
        cid = self._extract_chat_id(update)
        if cid: self.add_chat_id(cid)

        help_msg = (
            f"📖 **HƯỚNG DẪN SỬ DỤNG ZALO BOT SOLAR CLEAN**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **Hỏi đáp & Ra lệnh AI tự nhiên:**\n"
            f"Bạn có thể nhắn bất kỳ câu nói nào để AI trả lời và thực thi:\n"
            f"• *'Rửa pin giúp tôi'* -> Kích hoạt PLC vệ sinh\n"
            f"• *'Hệ thống đang chạy hay dừng?'* -> Báo cáo trạng thái\n"
            f"• *'Công suất phát điện hiện tại là bao nhiêu?'*\n"
            f"• *'Tấm pin có bị lá cây hay phân chim che không?'*\n"
            f"• *'Đặt ngưỡng bẩn thành 8%'*\n"
            f"• *'Đổi IP PLC thành 192.168.1.50'*\n\n"
            f"📌 **Danh sách Lệnh Nhanh:**\n"
            f"• `/status` - Báo cáo tổng thể hệ thống\n"
            f"• `/clean` - Kích hoạt rửa pin ngay lập tức\n"
            f"• `/power` - Xem thông số công suất điện\n"
            f"• `/startsys` - Khởi động giám sát\n"
            f"• `/stop` - Dừng giám sát\n"
            f"• `/help` - Xem lại hướng dẫn này"
        )
        await update.message.reply_text(help_msg)


    # ── AI Ollama Chat Handler ──

    async def _handle_ai_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Xử lý tin nhắn văn bản bằng AI Ollama (qwen2.5:0.5b)."""
        try:
            if not update.message or not update.message.text:
                return

            user_text = update.message.text.strip()
            chat_id = self._extract_chat_id(update)
            
            # Tự động lưu chat_id
            if chat_id:
                self.add_chat_id(chat_id)

            # 1. Gửi action "Đang soạn tin..." (TYPING)
            try:
                if hasattr(update.message, 'reply_action'):
                    await update.message.reply_action(ChatAction.TYPING)
                elif chat_id and hasattr(context, 'bot') and hasattr(context.bot, 'send_chat_action'):
                    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except Exception:
                pass


            # 2. Đọc trạng thái trạm pin thực tế
            current_res = self._get_current_results()

            # 3. Chuyển cho AI Engine (ai_assistant.py)
            from ai_assistant import ai_engine
            
            # Chạy chat trong thread executor để không block asyncio loop
            loop = asyncio.get_running_loop()
            ai_res = await loop.run_in_executor(
                None,
                lambda: ai_engine.chat(
                    user_message=user_text,
                    current_results=current_res,
                    command_queue=self.command_queue
                )
            )

            reply_text = ai_res.get('reply', 'Tôi đã ghi nhận câu hỏi của bạn.')
            
            # 4. Gửi câu trả lời về cho người dùng
            sent = False
            if hasattr(update.message, 'reply_text'):
                try:
                    await update.message.reply_text(reply_text)
                    sent = True
                except Exception as ex:
                    print(f"⚠️ [Zalo Bot] reply_text failed: {ex}")
            if not sent and chat_id and hasattr(context, 'bot'):
                await context.bot.send_message(chat_id=chat_id, text=reply_text)

        except Exception as e:
            print(f"❌ [Zalo Bot] Lỗi xử lý tin nhắn AI: {e}")
            traceback.print_exc()
            try:
                if chat_id and hasattr(context, 'bot'):
                    await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Đang gặp sự cố xử lý câu hỏi: {str(e)}")
            except Exception:
                pass


    # ── Smart Notification & Alerts ──

    def _can_send_alert(self, alert_key: str) -> bool:
        """Kiểm tra Cooldown chống spam cảnh báo."""
        cooldown = float(self.config.get('alert_cooldown_seconds', 600))
        now = time.time()
        last_time = self._last_alert_times.get(alert_key, 0.0)
        if (now - last_time) >= cooldown:
            self._last_alert_times[alert_key] = now
            return True
        return False

    def send_broadcast_message(self, text: str, alert_key: Optional[str] = None) -> bool:
        """
        Gửi tin nhắn cảnh báo tới toàn bộ danh sách Admin Chat IDs (Thread-safe).
        """
        if not self.config.get('enabled', True) or not ZALO_BOT_AVAILABLE:
            return False

        if alert_key and not self._can_send_alert(alert_key):
            print(f"⏳ [Zalo Alert] Bỏ qua cảnh báo '{alert_key}' do đang trong thời gian Cooldown.")
            return False

        chat_ids = self.config.get('admin_chat_ids', [])
        token = self.config.get('bot_token', '')

        if not token or not chat_ids:
            print(f"⚠️ [Zalo Alert] Chưa có Token hoặc danh sách Chat ID nhận tin.")
            return False

        def _send_task():
            async def _async_send():
                bot = Bot(token)
                try:
                    async with bot:
                        for cid in chat_ids:
                            try:
                                await bot.send_message(chat_id=str(cid), text=text)
                                print(f"📤 [Zalo Alert] Đã gửi cảnh báo tới Chat ID: {cid}")
                            except Exception as ex:
                                print(f"❌ [Zalo Alert] Lỗi gửi tới Chat ID {cid}: {ex}")
                except Exception as e:
                    print(f"❌ [Zalo Alert] Lỗi khởi tạo Bot gửi tin: {e}")

            asyncio.run(_async_send())

        threading.Thread(target=_send_task, daemon=True).start()
        return True

    def notify_dirt_detected(self, area_ratio: float, dirty_patches: int, total_patches: int = 32, power_watts: float = 0.0, plc_triggered: bool = True):
        """Cảnh báo phát hiện bụi bẩn vượt ngưỡng."""
        if not self.config.get('alert_on_dirt', True):
            return

        pct = area_ratio * 100
        msg = (
            f"🚨 **CẢNH BÁO: PHÁT HIỆN TẤM PIN BỊ BỤI BẨN!** 🚨\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧹 **Tỷ lệ bẩn:** `{pct:.1f}%` ({dirty_patches}/{total_patches} ô bẩn)\n"
            f"⚡ **Công suất hiện tại:** `{power_watts:.1f} W`\n"
            f"🔌 **Xử lý PLC:** {'✅ Đã kích hoạt vòi xịt & chổi lau' if plc_triggered else '⚠️ Chưa kích hoạt (Chế độ thủ công/Chưa kết nối)'}\n"
            f"⏱️ **Thời gian:** {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Gõ `/status` để xem chi tiết hoặc `/clean` để rửa lại."
        )
        self.send_broadcast_message(msg, alert_key="dirt_alert")

    def notify_debris_detected(self, debris_list: List[str], area_ratio: float = 0.0, plc_triggered: bool = True):
        """Cảnh báo phát hiện vật cản (lá cây, phân chim) từ YOLO."""
        if not self.config.get('alert_on_debris', True):
            return

        debris_trans = {
            'leaf': 'Lá cây 🍃',
            'lá cây': 'Lá cây 🍃',
            'bird_drop': 'Phân chim 🐦',
            'phân chim': 'Phân chim 🐦'
        }
        debris_names = [debris_trans.get(d.lower(), d) for d in debris_list]
        debris_str = ", ".join(set(debris_names))

        msg = (
            f"🍂 **CẢNH BÁO: PHÁT HIỆN VẬT CẢN TRÊN PIN (YOLO)** 🍂\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **Vật cản phát hiện:** {debris_str}\n"
            f"🧹 **Mức độ bẩn kèm theo:** `{area_ratio * 100:.1f}%`\n"
            f"🔌 **Hành động:** {'✅ Đã tự động kích hoạt PLC làm sạch' if plc_triggered else '⚠️ Cần kiểm tra làm sạch bề mặt'}\n"
            f"⏱️ **Thời gian:** {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_broadcast_message(msg, alert_key="debris_alert")

    def notify_crack_detected(self, crack_list: List[str]):
        """Cảnh báo phát hiện nứt vỡ tấm pin (nguy hiểm)."""
        if not self.config.get('alert_on_crack', True):
            return

        msg = (
            f"⚡🚨 **CẢNH BÁO KHẨN CẤP: PHÁT HIỆN NỨT VỠ TẤM PIN!** 🚨⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💥 **Phát hiện:** Vết nứt vỡ bề mặt tấm quang điện (`crack`)\n"
            f"⚠️ **Khuyến nghị:** Yêu cầu kỹ thuật viên kiểm tra trực tiếp ngay để tránh rò điện và chập cháy!\n"
            f"⏱️ **Thời gian:** {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        self.send_broadcast_message(msg, alert_key="crack_alert")

    # ── Bot Lifecycle Management (Polling Thread) ──

    def start(self):
        """Khởi động Bot polling trong daemon thread."""
        if not ZALO_BOT_AVAILABLE:
            print("⚠️ [Zalo Bot] Thư viện python-zalo-bot chưa được cài đặt.")
            return

        if not self.config.get('enabled', True):
            print("ℹ️ [Zalo Bot] Tính năng Zalo Bot đang TẮT trong cấu hình.")
            return

        token = self.config.get('bot_token', '').strip()
        if not token:
            print("⚠️ [Zalo Bot] Chưa cấu hình BOT TOKEN.")
            return

        if self.is_running:
            print("ℹ️ [Zalo Bot] Bot đang chạy rồi.")
            return

        self.is_running = True
        self.bot_thread = threading.Thread(target=self._run_bot_loop, args=(token,), daemon=True)
        self.bot_thread.start()
        print(f"🚀 [Zalo Bot] Đang khởi chạy tiến trình Long Polling...")

    def _run_bot_loop(self, token: str):
        """Vòng lặp chính chạy trong thread riêng."""
        try:
            # Khởi tạo application
            builder = ApplicationBuilder().token(token)
            app = builder.build()
            self.bot_app = app

            # Đăng ký Command Handlers
            app.add_handler(CommandHandler("start", self._handle_start))
            app.add_handler(CommandHandler("status", self._handle_status))
            app.add_handler(CommandHandler("clean", self._handle_clean))
            app.add_handler(CommandHandler("power", self._handle_power))
            app.add_handler(CommandHandler("startsys", self._handle_startsys))
            app.add_handler(CommandHandler("stop", self._handle_stop))
            app.add_handler(CommandHandler("help", self._handle_help))

            # Đăng ký AI Message Handler (xử lý văn bản chat tự nhiên)
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_ai_message))

            print("🤖 [Zalo Bot] Bắt đầu nhận tin nhắn (Long Polling)...")
            app.run_polling()

        except Exception as e:
            print(f"❌ [Zalo Bot] Dừng với lỗi: {e}")
            traceback.print_exc()
        finally:
            self.is_running = False
            print("⏹️ [Zalo Bot] Đã dừng tiến trình bot.")

    def stop(self):
        """Dừng Bot."""
        if not self.is_running:
            return
        self.is_running = False
        try:
            if self.bot_app:
                self.bot_app._running = False
        except Exception:
            pass
        print("⏹️ [Zalo Bot] Yêu cầu dừng bot...")


    def restart(self):
        """Khởi động lại Bot."""
        self.stop()
        time.sleep(1)
        self.start()


# Global Singleton Instance
zalo_service = ZaloService()
