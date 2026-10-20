"""
tools/test_zalo_service.py — Test script for Zalo Bot & AI Integration
"""
import os
import sys
import time
import json
import queue

# Windows console encoding fix
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zalo_service import zalo_service
from ai_assistant import ai_engine

def test_ai_chat_with_intent():
    print("\n--- 1. TEST AI OLLAMA CHAT & INTENT EXECUTION ---")
    mock_cmd_queue = queue.Queue()
    mock_results = {
        'p_dirty': 0.18,
        'area_ratio': 0.187,
        'label_name': 'ban',
        'status': 'Cần vệ sinh',
        'is_running': True,
        'clean_count': 3,
        'plc_connected': True,
        'plc_status': 'Connected',
        'plc_ip': '192.168.1.11',
        'power_voltage': 24.5,
        'power_current': 3.2,
        'power_watts': 78.4,
        'power_energy': 1.45,
        'dirty_patch_count': 6,
        'valid_patch_count': 32,
        'yolo_clean_faults': ['leaf'],
        'yolo_crack_faults': []
    }

    # Test Intent: Clean
    print("User hỏi: 'Tấm pin đang thế nào rồi, rửa pin giúp tôi'")
    res1 = ai_engine.chat("Tấm pin đang thế nào rồi, rửa pin giúp tôi", current_results=mock_results, command_queue=mock_cmd_queue)
    print(f"AI Phản hồi:\n{res1.get('reply')}")
    print(f"Lệnh phát hiện: {res1.get('action')}")
    
    if not mock_cmd_queue.empty():
        cmd = mock_cmd_queue.get()
        print(f"✅ Đã phát lệnh vào hàng đợi điều khiển PLC: {cmd}")
    else:
        print("⚠️ Chưa có lệnh trong hàng đợi")

    # Test Math / Quick question
    print("\nUser hỏi: '3 + 5 bằng mấy'")
    res2 = ai_engine.chat("3 + 5 bằng mấy", current_results=mock_results, command_queue=mock_cmd_queue)
    print(f"AI Phản hồi: {res2.get('reply')}")


def test_zalo_service_alerts():
    print("\n--- 2. TEST ZALO SERVICE STATUS & ALERTS ---")
    status = zalo_service.get_status()
    print("Zalo Service Status:", json.dumps(status, indent=2, ensure_ascii=False))

    # Test alert formation
    print("\nSimulating Dirty Alert...")
    zalo_service.notify_dirt_detected(
        area_ratio=0.187,
        dirty_patches=6,
        total_patches=32,
        power_watts=78.4,
        plc_triggered=True
    )

    print("\nSimulating Debris Alert (YOLO)...")
    zalo_service.notify_debris_detected(
        debris_list=['leaf', 'bird_drop'],
        area_ratio=0.187,
        plc_triggered=True
    )


if __name__ == "__main__":
    print("🚀 Bắt đầu kiểm tra hệ thống Zalo Bot & AI...")
    test_ai_chat_with_intent()
    test_zalo_service_alerts()
    print("\n✅ Hoàn tất kiểm thử Zalo Service & AI Assistant!")
