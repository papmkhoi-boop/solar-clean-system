"""
cloud_api_client.py — Cloud API Client for Desktop App
======================================================
Gửi dữ liệu từ Desktop App lên Cloud Server qua HTTPS API.
Desktop chạy module này trong background thread.

Usage:
    from cloud_api_client import CloudAPIClient
    client = CloudAPIClient(
        cloud_url='https://solar.yourdomain.com',
        api_key='your-device-api-key'
    )
    client.start()

    # Gọi từ main loop:
    client.push_status(results_dict)
    client.push_frame(jpeg_bytes, 'main')
    client.push_power(reading_dict)
"""

import os
import sys
import time
import json
import threading
import traceback
from datetime import datetime

# Use urllib for zero-dependency HTTP client (no need for requests package)
import urllib.request
import urllib.error
import urllib.parse


class CloudAPIClient:
    """
    Gửi dữ liệu từ Desktop App lên Cloud Server qua HTTPS API.
    Thread-safe — có thể gọi push_*() từ bất kỳ thread nào.
    """

    def __init__(self, cloud_url: str, api_key: str, device_id: str = 'device-001'):
        # Bỏ trailing slash
        self.cloud_url = cloud_url.rstrip('/')
        self.api_key = api_key
        self.device_id = device_id

        # State
        self._running = False
        self._connected = False
        self._last_error = None
        self._last_heartbeat = 0
        self._heartbeat_interval = 10  # seconds
        self._command_poll_interval = 3  # seconds
        self._last_command_poll = 0

        # Threads
        self._heartbeat_thread = None

        # Command callback
        self._command_callback = None

        # Stats
        self._push_count = 0
        self._error_count = 0
        self._last_push_time = 0

        print(f"[Cloud] CloudAPIClient: url={self.cloud_url}, device={self.device_id}")

    # ==================== HTTP HELPERS ====================

    def _make_headers(self, content_type: str = 'application/json') -> dict:
        """Create request headers with API key."""
        headers = {
            'X-API-Key': self.api_key,
            'User-Agent': 'SolarPanel-Desktop/3.0',
        }
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    def _post_json(self, endpoint: str, data: dict) -> dict | None:
        """POST JSON data to cloud API."""
        url = f"{self.cloud_url}{endpoint}"
        try:
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(
                url, data=body,
                headers=self._make_headers('application/json'),
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                self._connected = True
                self._push_count += 1
                self._last_push_time = time.time()
                return result
        except urllib.error.HTTPError as e:
            self._last_error = f"HTTP {e.code}: {e.reason}"
            self._error_count += 1
            if e.code == 403:
                print(f"[Cloud] ERROR: API Key invalid! Check CLOUD_API_KEY")
            return None
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            self._error_count += 1
            return None

    def _post_binary(self, endpoint: str, data: bytes,
                     content_type: str = 'image/jpeg',
                     params: dict = None) -> dict | None:
        """POST binary data (images) to cloud API."""
        url = f"{self.cloud_url}{endpoint}"
        if params:
            url += '?' + urllib.parse.urlencode(params)
        try:
            headers = self._make_headers(content_type)
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                self._connected = True
                self._push_count += 1
                return result
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            self._error_count += 1
            return None

    def _get_json(self, endpoint: str) -> dict | None:
        """GET JSON data from cloud API."""
        url = f"{self.cloud_url}{endpoint}"
        try:
            req = urllib.request.Request(url, headers=self._make_headers(None), method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                self._connected = True
                return result
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            return None

    def _post_multipart(self, endpoint: str, filepath: str,
                        fields: dict = None) -> dict | None:
        """POST multipart/form-data file upload."""
        url = f"{self.cloud_url}{endpoint}"
        try:
            boundary = f'----SolarUpload{int(time.time()*1000)}'
            body = b''

            # Add text fields
            if fields:
                for key, val in fields.items():
                    body += f'--{boundary}\r\n'.encode()
                    body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
                    body += f'{val}\r\n'.encode()

            # Add file
            filename = os.path.basename(filepath)
            body += f'--{boundary}\r\n'.encode()
            body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
            body += b'Content-Type: image/jpeg\r\n\r\n'
            with open(filepath, 'rb') as f:
                body += f.read()
            body += b'\r\n'
            body += f'--{boundary}--\r\n'.encode()

            headers = self._make_headers(f'multipart/form-data; boundary={boundary}')
            req = urllib.request.Request(url, data=body, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                self._connected = True
                self._push_count += 1
                return result
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            self._error_count += 1
            return None

    # ==================== PUBLIC API ====================

    def push_status(self, results: dict) -> bool:
        """
        Gửi AI status JSON lên cloud.
        Gọi từ main AI loop, mỗi 1-3 giây.
        """
        if not self._running:
            return False
        result = self._post_json('/api/device/status', results)
        return result is not None and result.get('ok', False)

    def push_frame(self, jpeg_bytes: bytes, frame_type: str = 'main') -> bool:
        """
        Gửi camera frame (JPEG bytes) lên cloud.
        frame_type: 'main', 'cnn_patch', 'yolo_panel'
        """
        if not self._running or not jpeg_bytes:
            return False
        result = self._post_binary(
            '/api/device/frame',
            jpeg_bytes,
            'image/jpeg',
            params={'frame_type': frame_type}
        )
        return result is not None and result.get('ok', False)

    def push_snapshot(self, filepath: str, ai_label: str = '',
                      ai_confidence: float = 0.0,
                      dirty_ratio: float = 0.0) -> bool:
        """Upload snapshot image file lên cloud."""
        if not self._running or not os.path.exists(filepath):
            return False
        result = self._post_multipart(
            '/api/device/snapshot',
            filepath,
            fields={
                'ai_label': ai_label,
                'ai_confidence': str(ai_confidence),
                'dirty_ratio': str(dirty_ratio),
            }
        )
        return result is not None and result.get('ok', False)

    def push_power(self, reading: dict) -> bool:
        """Gửi power reading lên cloud."""
        if not self._running:
            return False
        result = self._post_json('/api/device/power', reading)
        return result is not None and result.get('ok', False)

    def push_cleaning_event(self, event: dict) -> bool:
        """Gửi cleaning event lên cloud."""
        if not self._running:
            return False
        result = self._post_json('/api/device/cleaning_event', event)
        return result is not None and result.get('ok', False)

    def poll_commands(self) -> list:
        """
        Lấy danh sách lệnh mới từ cloud.
        Desktop gọi định kỳ (mỗi 3-5 giây).
        Returns list of {'command': str, 'value': str}
        """
        result = self._get_json('/api/device/commands')
        if result and 'commands' in result:
            return result['commands']
        return []

    def heartbeat(self) -> bool:
        """Gửi heartbeat signal."""
        result = self._post_json('/api/device/heartbeat', {})
        return result is not None and result.get('ok', False)

    # ==================== BACKGROUND THREADS ====================

    def set_command_callback(self, callback):
        """
        Đặt callback xử lý commands từ cloud.
        callback(command: str, value: str)
        """
        self._command_callback = callback

    def start(self):
        """Bắt đầu background threads (heartbeat + command polling)."""
        if self._running:
            return
        self._running = True

        # Test connection
        if self.heartbeat():
            print(f"[Cloud] Connected: {self.cloud_url}")
            self._connected = True
        else:
            print(f"[Cloud] WARN: Cloud unreachable: {self.cloud_url} (will retry)")
            self._connected = False

        # Start heartbeat + command poll thread
        self._heartbeat_thread = threading.Thread(
            target=self._background_loop, daemon=True, name='CloudAPI'
        )
        self._heartbeat_thread.start()

    def stop(self):
        """Dừng background threads."""
        self._running = False

    def _background_loop(self):
        """Background thread: heartbeat + poll commands."""
        while self._running:
            try:
                now = time.time()

                # Heartbeat
                if now - self._last_heartbeat >= self._heartbeat_interval:
                    self.heartbeat()
                    self._last_heartbeat = now

                # Poll commands
                if now - self._last_command_poll >= self._command_poll_interval:
                    commands = self.poll_commands()
                    self._last_command_poll = now

                    if commands and self._command_callback:
                        for cmd in commands:
                            try:
                                command = cmd.get('command', '')
                                value_raw = cmd.get('value', '')
                                # Parse JSON value if possible
                                try:
                                    value = json.loads(value_raw) if value_raw else None
                                except (json.JSONDecodeError, TypeError):
                                    value = value_raw
                                self._command_callback(command, value)
                                print(f"[Cloud] Command: {command} = {value}")
                            except Exception as e:
                                print(f"[Cloud] Command handler error: {e}")

            except Exception as e:
                if self._connected:
                    print(f"[Cloud] Background error: {e}")
                    self._connected = False

            time.sleep(1)

    # ==================== STATUS ====================

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def stats(self) -> dict:
        return {
            'connected': self._connected,
            'cloud_url': self.cloud_url,
            'push_count': self._push_count,
            'error_count': self._error_count,
            'last_error': self._last_error,
            'last_push_time': self._last_push_time,
        }
