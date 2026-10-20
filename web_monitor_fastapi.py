"""
Web Monitor cho Há»‡ Thá»‘ng Vá»‡ Sinh Táº¥m Pin - FastAPI Version
============================================================
Thay tháº¿ Flask báº±ng FastAPI:
  - Async native (nhanh hÆ¡n 3-5x)
  - WebSocket real-time (thay vÃ¬ polling /api/status má»—i 500ms)
  - Auto API docs táº¡i /docs (Swagger UI)
  - Báº£o máº­t tá»‘t hÆ¡n (secrets.compare_digest, whitelist static, auth snapshots)
  - Production-ready vá»›i uvicorn ASGI server

Truy cáº­p: http://localhost:5000 hoáº·c http://<IP>:5000
API Docs: http://localhost:5000/docs
"""

import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
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
def _normalize_windows_path(path: str) -> str:
    """Convert extended Windows paths so Jinja/FileSystemLoader can read templates."""
    if os.name == "nt" and path.startswith("\\\\?\\"):
        return path[4:]
    return path
import cv2
import numpy as np

import time

import asyncio

import secrets

import threading

import queue

import traceback

import json

import hashlib

import uuid

from datetime import datetime

from pathlib import Path

from typing import Optional


from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, status, Request, Cookie, Form, Response

from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse, FileResponse, RedirectResponse

from fastapi.security import HTTPBasic, HTTPBasicCredentials

from fastapi.templating import Jinja2Templates



# ==================== ACCOUNT MANAGEMENT ====================
_SOURCE_DIR = _normalize_windows_path(os.path.dirname(os.path.abspath(__file__)))
if getattr(sys, 'frozen', False):
    _RUNTIME_DIR = _normalize_windows_path(os.path.dirname(sys.executable))
else:
    _RUNTIME_DIR = _SOURCE_DIR
ACCOUNTS_DIR = os.path.join(_RUNTIME_DIR, 'taikhoan')
ACCOUNTS_FILE = os.path.join(ACCOUNTS_DIR, 'accounts.json')
SESSIONS_FILE = os.path.join(ACCOUNTS_DIR, 'sessions.json')
_accounts_lock = threading.Lock()
_sessions_lock = threading.Lock()


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt"""
    salt = 'solarpanel2025'
    return hashlib.sha256(f'{salt}:{password}'.encode()).hexdigest()


def _load_accounts() -> list:
    """Load accounts from JSON file"""
    with _accounts_lock:
        try:
            if os.path.exists(ACCOUNTS_FILE):
                with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('accounts', [])
        except Exception as e:
            print(f"âŒ Load accounts error: {e}")
    return []


def _save_accounts(accounts: list):
    """Save accounts to JSON file"""
    with _accounts_lock:
        try:
            os.makedirs(ACCOUNTS_DIR, exist_ok=True)
            with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'accounts': accounts}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"âŒ Save accounts error: {e}")


def _find_account(username: str) -> dict | None:
    """Find account by username"""
    accounts = _load_accounts()
    for acc in accounts:
        if acc.get('username', '').lower() == username.lower():
            return acc
    return None


def _check_user_password(username: str, password: str) -> tuple[bool, str]:
    """
    Check user credentials. Returns (success, role).
    Admin master account always works.
    """
    # Master admin account (always works)
    if (secrets.compare_digest(username.encode(), CONFIG['AUTH_USERNAME'].encode()) and
            secrets.compare_digest(password.encode(), CONFIG['AUTH_PASSWORD'].encode())):
        return True, 'admin'
    
    # Check registered accounts
    acc = _find_account(username)
    if acc is None:
        return False, ''
    
    if acc.get('status') != 'approved':
        return False, 'pending'  # Account not yet approved
    
    pw_hash = _hash_password(password)
    if secrets.compare_digest(pw_hash.encode(), acc.get('password_hash', '').encode()):
        return True, acc.get('role', 'user')
    
    return False, ''

# Import snap7 for PLC
try:
    import snap7
    SNAP7_AVAILABLE = True
    print("âœ… snap7 available")
except ImportError:
    SNAP7_AVAILABLE = False
    print("âš ï¸  snap7 not available - PLC features disabled")

# Import TFLite
try:
    import tflite_runtime.interpreter as tflite
    TFLITE_RUNTIME = True
    print("âœ… Using tflite_runtime")
except ImportError:
    try:
        import tensorflow as tf
        TFLITE_RUNTIME = False
        print("âš ï¸   Using tensorflow.lite")
    except ImportError:
        print("â Œ Neither tflite-runtime nor tensorflow is installed!")

# ==================== CONFIGURATION ====================
CONFIG = {
    'MODEL_PATH': 'buiban.h5',
    'LABELS_PATH': 'labels_2classes.txt',
    'IMG_SIZE': (224, 224),
    'DIRT_THRESHOLD': 0.06,
    'DIRT_AREA_THRESHOLD': 0.06,
    'CAMERA_ID': 0,
    'FRAME_ROTATION_MODE': 'none',
    'FORCE_PORTRAIT_FRAME': True,
    'PORTRAIT_ROTATION': 'ccw',
    'PLC_IP': '192.168.1.1',
    'WEB_HOST': '0.0.0.0',
    'WEB_PORT': 5000,
    'TRIGGER_CLASS': 'ban',

    'SNAPSHOT_INTERVAL': 600,

    'MIN_CONFIDENCE': 0.60,

    'CNN_DIRTY_THRESHOLD': 0.05,

    # Authentication - Ä á»”I Máº¬T KHáº¨U TRÆ¯á»šC KHI DEPLOY

    'AUTH_USERNAME': os.environ.get('WEB_USERNAME', 'admin'),

    'AUTH_PASSWORD': os.environ.get('WEB_PASSWORD', 'admin'),
}

def _get_plc_ip(config: dict | None = None) -> str:
    """Read PLC IP from either desktop nested config or web flat config."""
    cfg = config or CONFIG
    plc_cfg = cfg.get('PLC') if isinstance(cfg, dict) else None
    if isinstance(plc_cfg, dict) and plc_cfg.get('IP'):
        return str(plc_cfg['IP'])
    return str(cfg.get('PLC_IP', CONFIG.get('PLC_IP', '192.168.1.1')))

def _set_plc_ip(config: dict | None, ip: str):
    """Write PLC IP to the active config shape and keep web flat config synced."""
    if config is None:
        config = CONFIG
    CONFIG['PLC_IP'] = ip
    plc_cfg = config.get('PLC') if isinstance(config, dict) else None
    if isinstance(plc_cfg, dict):
        plc_cfg['IP'] = ip
    else:
        config['PLC_IP'] = ip

def normalize_frame_orientation(frame, config):
    """Keep preview frames portrait when the panel/camera is installed vertically."""
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

def _cnn_probs_2class(pred_probs) -> list[float]:
    """Return CNN probabilities in the current 2-class order: [sach, ban]."""
    try:
        probs = [float(p) for p in pred_probs]
    except Exception:
        return [0.0, 0.0]
    if len(probs) >= 2:
        return probs[:2]
    if len(probs) == 1:
        return [probs[0], 0.0]
    return [0.0, 0.0]
# ==================== FASTAPI APP ====================
app = FastAPI(
    title="Há»‡ Thá»‘ng Vá»‡ Sinh Táº¥m Pin Máº·t Trá»i",
    version="2.5.0-FastAPI",
    docs_url=None,      # Táº¯t Swagger UI â€” khÃ´ng hiá»‡n API ra ngoÃ i
    redoc_url=None,
    openapi_url=None,   # Táº¯t luÃ´n /openapi.json
)

# Exception handler: redirect 302 to login page
class _RedirectToLogin(HTTPException):
    def __init__(self):
        super().__init__(status_code=303, detail='Redirect to login')

@app.exception_handler(_RedirectToLogin)
async def redirect_to_login_handler(request: Request, exc: _RedirectToLogin):
    return RedirectResponse('/login', status_code=302)

# Security â€” cookie-based session (replaces browser Basic Auth popup)
security = HTTPBasic(auto_error=False)
_sessions: dict[str, dict] = {}  # token â†’ {username, created}

def _load_sessions():
    """Load saved login sessions so mobile users stay signed in after restart."""
    with _sessions_lock:
        try:
            if os.path.exists(SESSIONS_FILE):
                with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions = data.get('sessions', {})
                if isinstance(sessions, dict):
                    _sessions.clear()
                    for token, session in sessions.items():
                        if isinstance(token, str) and isinstance(session, dict):
                            username = str(session.get('username', '')).strip()
                            if username:
                                _sessions[token] = {
                                    'username': username,
                                    'created': float(session.get('created', time.time())),
                                    'role': str(session.get('role', 'user')),
                                }
        except Exception as e:
            print(f"âŒ Load sessions error: {e}")

def _save_sessions():
    """Persist current login sessions to disk."""
    with _sessions_lock:
        try:
            os.makedirs(ACCOUNTS_DIR, exist_ok=True)
            with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump({'sessions': _sessions}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"âŒ Save sessions error: {e}")

_load_sessions()

# Templates â€” há»— trá»£ cáº£ cháº¡y .py vÃ  .exe (PyInstaller)
if getattr(sys, 'frozen', False):
    _base_dir = _normalize_windows_path(sys._MEIPASS)
else:
    _base_dir = _SOURCE_DIR
templates = Jinja2Templates(directory=os.path.join(_base_dir, "templates"))

# ==================== GLOBAL STATE ====================

app_instance = None  # Reference to desktop app (set tá»« solar_panel_plc_auto_tflite.py)

detector = None

camera = None

is_running = False


lock = threading.Lock()

current_frame = None
current_frame_bytes = None  # Pre-encoded JPEG bytes (trÃ¡nh encode láº¡i)
current_cnn_patch_bytes = None
current_yolo_panel_bytes = None
current_results = {
    'p_dirty': 0.0,
    'area_ratio': 0.0,
    'predicted_class': 0,
    'label_name': 'Unknown',
    'pred_probs': [0.0, 0.0],
    'class_names': ['sach', 'ban'],
    'model_pipeline': 'CNN 2-class + YOLO/Panel-Seg auxiliaries',
    'status': 'Initializing...',

    'status_color': 'warning',

    'timestamp': time.time(),

    'fps': 0.0,

    'clean_count': 0,
    'plc_connected': False,
    'plc_status': 'Not Connected',
    'confidence': 0.0,
    'dirty_patch_count': 0,
    'valid_patch_count': 0,
    'nopanel_patch_count': 0,
    'cnn_active': False,
    'panel_detected': False,
    'yolo_clean_faults': [],
    'yolo_crack_faults': [],
    'last_snapshot_path': None,
    'last_snapshot_time': None,

    'next_snapshot': 0,

    'snapshot_interval': 600,

    # Settings sync (App â†’ Web)

    'dirt_threshold': 0.0,

    'camera_id': 0,

    'is_running': False,

    'min_confidence': 0.60,

    'plc_ip': '192.168.1.1',

}


# Command queue - giao tiáº¿p thread-safe vá»›i Desktop App

command_queue = queue.Queue()


# Reference Ä‘áº¿n CONFIG gá»‘c cá»§a Desktop App (set bá»Ÿi start_web_server())

# QUAN TRá»ŒNG: KhÃ´ng dÃ¹ng `from solar_panel_plc_auto_tflite import CONFIG`

# vÃ¬ khi cháº¡y trá»±c tiáº¿p, module lÃ  __main__ â†’ import táº¡o báº£n CONFIG thá»© 2!

APP_CONFIG_REF = None


# ==================== WEBSOCKET MANAGER ====================
from starlette.websockets import WebSocketState

class ConnectionManager:
    """Quản lý WebSocket connections cho real-time push"""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WS] WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WS] WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict):
        """Gửi data đến tất cả clients an toàn"""
        disconnected = []
        for conn in self.active_connections:
            try:
                if conn.client_state == WebSocketState.CONNECTED:
                    await conn.send_json(data)
                else:
                    disconnected.append(conn)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)


ws_manager = ConnectionManager()



# ==================== WHITELIST STATIC ====================

# Chá»‰ cho phÃ©p truy cáº­p file cá»¥ thá»ƒ - CHáº¶N lá»™ source code

ALLOWED_STATIC_FILES = {'ctut.webp', 'ctut.png', 'ctut.jpg', 'favicon.ico'}



# ==================== AUTHENTICATION (Cookie Session) ====================

def _check_password(username: str, password: str) -> bool:

    """Timing-safe credential check â€” supports both admin and registered accounts"""

    ok, role = _check_user_password(username, password)

    return ok



def _get_session_user(request: Request) -> str | None:
    """Get username from session cookie, or None"""
    token = request.cookies.get('session')
    session = _get_active_session(token)
    return session['username'] if session else None

def _get_active_session(token: str | None) -> dict | None:
    """Return a saved session only if its account is still allowed."""
    if not token or token not in _sessions:
        return None

    session = _sessions[token]
    username = str(session.get('username', ''))
    if _is_session_user_active(username):
        return session
    # The account was deleted, rejected, or disabled after the token was issued.
    del _sessions[token]
    _save_sessions()
    return None

def _is_session_user_active(username: str) -> bool:
    """Return True when an existing session should still be accepted."""
    if username.lower() == CONFIG['AUTH_USERNAME'].lower():
        return True
    acc = _find_account(username)
    return bool(acc and acc.get('status') == 'approved')

def _drop_sessions_for_user(username: str):
    """Invalidate every saved session for one username."""
    stale_tokens = [
        token
        for token, session in _sessions.items()
        if str(session.get('username', '')).lower() == username.lower()
    ]
    for token in stale_tokens:
        del _sessions[token]
    if stale_tokens:
        _save_sessions()


async def verify_credentials(request: Request):

    """Check session cookie â†’ if invalid, redirect to /login (HTML) or 401 (API)"""

    user = _get_session_user(request)

    if user:

        return user

    # Fallback: accept HTTP Basic for API clients (curl, etc.)

    creds = await security(request)

    if creds and _check_password(creds.username, creds.password):

        return creds.username

    # Not authenticated

    path = request.url.path

    if path.startswith('/api/') or path == '/video_feed':

        raise HTTPException(status_code=401, detail='Not authenticated')

    raise _RedirectToLogin()



def _is_admin(request: Request) -> bool:

    """Check if current user is admin"""

    user = _get_session_user(request)

    if user and user.lower() == CONFIG['AUTH_USERNAME'].lower():
        return True
    token = request.cookies.get('session')
    session = _get_active_session(token)
    if session:
        return session.get('role') == 'admin'
    return False


@app.get('/login', response_class=HTMLResponse)
async def login_page(request: Request, error: str = ''):
    """Professional login page"""
    # Already logged in? â†’ redirect home
    if _get_session_user(request):
        return RedirectResponse('/', status_code=302)
    return templates.TemplateResponse('login.html', {'request': request, 'error': error})


@app.post('/login')
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form â€” supports admin + registered accounts"""
    ok, role = _check_user_password(username, password)
    if ok:
        token = secrets.token_urlsafe(32)
        _sessions[token] = {'username': username, 'created': time.time(), 'role': role}
        _save_sessions()
        response = RedirectResponse('/', status_code=302)
        response.set_cookie('session', token, httponly=True, samesite='lax', max_age=315360000)
        return response

    # Check if account is pending approval

    if role == 'pending':

        return templates.TemplateResponse('login.html', {

            'request': request,

            'error': 'TÃ i khoáº£n Ä‘ang chá» duyá»‡t. Vui lÃ²ng liÃªn há»‡ quáº£n trá»‹ viÃªn.'

        }, status_code=401)


    return templates.TemplateResponse('login.html', {

        'request': request, 'error': 'Sai tÃ i khoáº£n hoáº·c máº­t kháº©u'

    }, status_code=401)



@app.get('/register', response_class=HTMLResponse)

async def register_page(request: Request, error: str = '', success: str = ''):

    """Registration page"""

    if _get_session_user(request):

        return RedirectResponse('/', status_code=302)

    return templates.TemplateResponse('register.html', {

        'request': request, 'error': error, 'success': success

    })



@app.post('/register')

async def register_submit(

    request: Request,

    username: str = Form(...),

    password: str = Form(...),

    password2: str = Form(...),

    fullname: str = Form('')

):

    """Process registration form"""

    # Validate

    username = username.strip()

    fullname = fullname.strip()


    if len(username) < 3:

        return templates.TemplateResponse('register.html', {

            'request': request, 'error': 'TÃªn tÃ i khoáº£n pháº£i cÃ³ Ã­t nháº¥t 3 kÃ½ tá»±'

        }, status_code=400)


    if len(password) < 4:

        return templates.TemplateResponse('register.html', {

            'request': request, 'error': 'Máº­t kháº©u pháº£i cÃ³ Ã­t nháº¥t 4 kÃ½ tá»±'

        }, status_code=400)


    if password != password2:

        return templates.TemplateResponse('register.html', {

            'request': request, 'error': 'Máº­t kháº©u nháº­p láº¡i khÃ´ng khá»›p'

        }, status_code=400)


    # Check if username already exists

    if username.lower() == CONFIG['AUTH_USERNAME'].lower():

        return templates.TemplateResponse('register.html', {

            'request': request, 'error': 'TÃªn tÃ i khoáº£n Ä‘Ã£ tá»“n táº¡i'

        }, status_code=400)


    existing = _find_account(username)

    if existing:

        return templates.TemplateResponse('register.html', {

            'request': request, 'error': 'TÃªn tÃ i khoáº£n Ä‘Ã£ tá»“n táº¡i'

        }, status_code=400)


    # Create new account (pending approval)

    accounts = _load_accounts()

    new_account = {

        'id': str(uuid.uuid4()),

        'username': username,

        'password_hash': _hash_password(password),

        'fullname': fullname,

        'status': 'pending',

        'role': 'user',

        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

        'approved_at': None,

    }

    accounts.append(new_account)

    _save_accounts(accounts)


    print(f"ðŸ“ New registration: {username} (pending approval)")


    # Notify desktop app via command queue

    command_queue.put(('new_registration', {'username': username, 'fullname': fullname}))


    return templates.TemplateResponse('register.html', {

        'request': request,

        'success': 'ÄÄƒng kÃ½ thÃ nh cÃ´ng! Vui lÃ²ng chá» quáº£n trá»‹ viÃªn duyá»‡t tÃ i khoáº£n.'

    })



@app.get('/logout')

async def logout(request: Request):

    """Clear session"""

    token = request.cookies.get('session')
    if token and token in _sessions:
        del _sessions[token]
        _save_sessions()
    response = RedirectResponse('/login', status_code=302)

    response.delete_cookie('session')

    return response



# ==================== ACCOUNT MANAGEMENT API (Admin only) ====================

@app.get('/api/accounts')

async def api_get_accounts(request: Request, username: str = Depends(verify_credentials)):

    """Get all registered accounts (admin only)"""

    if not _is_admin(request):

        raise HTTPException(status_code=403, detail='Admin only')

    accounts = _load_accounts()

    # Don't expose password hashes

    safe = [{k: v for k, v in acc.items() if k != 'password_hash'} for acc in accounts]

    return JSONResponse(content={'accounts': safe})



@app.post('/api/accounts/{account_id}/approve')

async def api_approve_account(account_id: str, request: Request, username: str = Depends(verify_credentials)):

    """Approve a pending account (admin only)"""

    if not _is_admin(request):

        raise HTTPException(status_code=403, detail='Admin only')

    accounts = _load_accounts()

    for acc in accounts:

        if acc['id'] == account_id:

            acc['status'] = 'approved'

            acc['approved_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            _save_accounts(accounts)

            print(f"âœ… Account approved: {acc['username']}")

            return JSONResponse(content={'success': True, 'message': f'ÄÃ£ duyá»‡t tÃ i khoáº£n {acc["username"]}'})

    raise HTTPException(status_code=404, detail='Account not found')



@app.post('/api/accounts/{account_id}/reject')

async def api_reject_account(account_id: str, request: Request, username: str = Depends(verify_credentials)):

    """Reject a pending account (admin only)"""

    if not _is_admin(request):

        raise HTTPException(status_code=403, detail='Admin only')

    accounts = _load_accounts()

    for acc in accounts:

        if acc['id'] == account_id:
            acc['status'] = 'rejected'
            _save_accounts(accounts)
            _drop_sessions_for_user(acc['username'])
            print(f"âŒ Account rejected: {acc['username']}")
            return JSONResponse(content={'success': True, 'message': f'ÄÃ£ tá»« chá»‘i tÃ i khoáº£n {acc["username"]}'})
    raise HTTPException(status_code=404, detail='Account not found')


@app.delete('/api/accounts/{account_id}')
async def api_delete_account(account_id: str, request: Request, username: str = Depends(verify_credentials)):
    """Delete an account (admin only)"""
    if not _is_admin(request):
        raise HTTPException(status_code=403, detail='Admin only')
    accounts = _load_accounts()
    for i, acc in enumerate(accounts):
        if acc['id'] == account_id:
            deleted = accounts.pop(i)
            _save_accounts(accounts)
            _drop_sessions_for_user(deleted['username'])
            print(f"ðŸ—‘ï¸ Account deleted: {deleted['username']}")
            return JSONResponse(content={'success': True, 'message': f'ÄÃ£ xÃ³a tÃ i khoáº£n {deleted["username"]}'})

    raise HTTPException(status_code=404, detail='Account not found')



@app.put('/api/accounts/{account_id}')

async def api_update_account(account_id: str, request: Request, username: str = Depends(verify_credentials)):

    """Update an account (admin only)"""

    if not _is_admin(request):

        raise HTTPException(status_code=403, detail='Admin only')

    data = await request.json()

    accounts = _load_accounts()

    for acc in accounts:

        if acc['id'] == account_id:

            if 'fullname' in data:

                acc['fullname'] = data['fullname']

            if 'role' in data:

                acc['role'] = data['role']

            if 'status' in data:

                acc['status'] = data['status']

            if 'password' in data and data['password']:
                acc['password_hash'] = _hash_password(data['password'])
            _save_accounts(accounts)
            if acc.get('status') != 'approved':
                _drop_sessions_for_user(acc['username'])
            print(f"âœï¸ Account updated: {acc['username']}")
            return JSONResponse(content={'success': True, 'message': f'ÄÃ£ cáº­p nháº­t tÃ i khoáº£n {acc["username"]}'})

    raise HTTPException(status_code=404, detail='Account not found')



@app.post('/api/register')

async def api_register(request: Request):

    """JSON API registration endpoint (for mobile app)"""

    try:

        data = await request.json()

    except Exception:

        raise HTTPException(status_code=400, detail='Invalid JSON')


    username = str(data.get('username', '')).strip()

    password = str(data.get('password', '')).strip()

    fullname = str(data.get('fullname', '')).strip()


    if len(username) < 3:

        return JSONResponse(content={'success': False, 'message': 'TÃªn tÃ i khoáº£n pháº£i cÃ³ Ã­t nháº¥t 3 kÃ½ tá»±'}, status_code=400)

    if len(password) < 4:

        return JSONResponse(content={'success': False, 'message': 'Máº­t kháº©u pháº£i cÃ³ Ã­t nháº¥t 4 kÃ½ tá»±'}, status_code=400)


    if username.lower() == CONFIG['AUTH_USERNAME'].lower():

        return JSONResponse(content={'success': False, 'message': 'TÃªn tÃ i khoáº£n Ä‘Ã£ tá»“n táº¡i'}, status_code=400)


    existing = _find_account(username)

    if existing:

        return JSONResponse(content={'success': False, 'message': 'TÃªn tÃ i khoáº£n Ä‘Ã£ tá»“n táº¡i'}, status_code=400)


    accounts = _load_accounts()

    new_account = {

        'id': str(uuid.uuid4()),

        'username': username,

        'password_hash': _hash_password(password),

        'fullname': fullname,

        'status': 'pending',

        'role': 'user',

        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

        'approved_at': None,

    }

    accounts.append(new_account)

    _save_accounts(accounts)


    print(f"ðŸ“ New registration (API): {username} (pending approval)")

    command_queue.put(('new_registration', {'username': username, 'fullname': fullname}))


    return JSONResponse(content={

        'success': True,

        'message': 'ÄÄƒng kÃ½ thÃ nh cÃ´ng! Vui lÃ²ng chá» quáº£n trá»‹ viÃªn duyá»‡t tÃ i khoáº£n.'

    })



# ==================== FRAME CAPTURE (Background Thread) ====================

def capture_frames():

    """

    Background thread - Tá»I Æ¯U HIá»†U NÄ‚NG:

    1. Láº¥y frame tá»« Desktop (khÃ´ng tranh camera)

    2. Pre-encode JPEG 1 láº§n (MJPEG + WebSocket dÃ¹ng chung)

    3. Giáº£m copy thá»«a, cache import ngoÃ i loop

    """

    global current_frame, current_frame_bytes, current_results, is_running, app_instance
    global current_cnn_patch_bytes, current_yolo_panel_bytes

    print("ðŸŽ¥ Web (FastAPI): Starting optimized frame capture...")


    if app_instance is None:

        print("âŒ Web: No Desktop App instance!")

        with lock:

            current_results['status'] = 'âŒ Chá»‰ hoáº¡t Ä‘á»™ng khi cháº¡y tá»« Desktop App'

            current_results['status_color'] = 'danger'

        return


    # DÃ¹ng APP_CONFIG_REF (reference trá»±c tiáº¿p Ä‘áº¿n CONFIG gá»‘c cá»§a __main__)

    # KHÃ”NG dÃ¹ng `from solar_panel_plc_auto_tflite import CONFIG` vÃ¬ táº¡o báº£n copy!

    APP_CONFIG = APP_CONFIG_REF if APP_CONFIG_REF is not None else CONFIG

    print(f"ðŸ”— capture_frames: APP_CONFIG_REF is {'SET (same as main CONFIG)' if APP_CONFIG_REF is not None else 'None (FALLBACK to web CONFIG!)'}")

    print(f"ðŸ”— APP_CONFIG id={id(APP_CONFIG)}, APP_CONFIG_REF id={id(APP_CONFIG_REF) if APP_CONFIG_REF else 'N/A'}")


    # Pre-allocate encode params

    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 65]

    frame_count = 0

    start_time = time.time()

    last_label = None

    last_snapshot_path_cache = None

    trigger_class = CONFIG['TRIGGER_CLASS']


    while is_running:

        try:

            # Desktop app chÆ°a start monitoring

            if not hasattr(app_instance, 'is_running') or not app_instance.is_running:

                with lock:

                    current_results['status'] = 'â¸ï¸ Desktop App chÆ°a báº¯t Ä‘áº§u'
                    current_results['status'] = 'â ¸ï¸  Desktop App chÆ°a báº¯t Ä‘áº§u'

                    current_results['status_color'] = 'warning'

                    # LuÃ´n sync settings dÃ¹ app chÆ°a cháº¡y â†’ web luÃ´n tháº¥y config má»›i

                    current_results['snapshot_interval'] = APP_CONFIG.get('SNAPSHOT_INTERVAL', CONFIG.get('SNAPSHOT_INTERVAL', 600))

                    current_results['dirt_threshold'] = APP_CONFIG.get('DIRT_AREA_THRESHOLD', CONFIG.get('DIRT_AREA_THRESHOLD', 0.0))

                    current_results['camera_id'] = APP_CONFIG.get('CAMERA_ID', CONFIG.get('CAMERA_ID', 0))

                    current_results['is_running'] = False

                    current_results['min_confidence'] = APP_CONFIG.get('MIN_CONFIDENCE', CONFIG.get('MIN_CONFIDENCE', 0.6))

                    current_results['cnn_dirty_threshold'] = APP_CONFIG.get('CNN_DIRTY_THRESHOLD', CONFIG.get('CNN_DIRTY_THRESHOLD', 0.65))

                    current_results['plc_ip'] = _get_plc_ip(APP_CONFIG)
                time.sleep(0.3)
                continue
            
            # LẤY FRAME TỪ DESKTOP (thread-safe, không gọi camera.read trực tiếp để tránh xung đột DirectShow)
            frame = getattr(app_instance, '_last_frame', None)
            if frame is None:
                with lock:
                    current_results['status'] = 'Dang cho frame tu Desktop...'
                    current_results['status_color'] = 'warning'
                time.sleep(0.1)
                continue
            frame = normalize_frame_orientation(frame, APP_CONFIG)
            
            frame_count += 1
            now = time.time()
            
            # Láº¤Y káº¿t quáº£ AI tá»« Desktop App (batch getattr)
            label_name = getattr(app_instance, '_last_label_name', 'Unknown')
            p_dirty = getattr(app_instance, '_last_p_dirty', 0.0)
            area_ratio = getattr(app_instance, '_last_area_ratio', 0.0)
            pred_probs = _cnn_probs_2class(getattr(app_instance, '_last_pred_probs', [0.0, 0.0]))
            pred_class = getattr(app_instance, '_last_pred_class', 0)
            confidence = getattr(app_instance, '_last_confidence', 0.0)
            dirty_patch_count = getattr(app_instance, '_last_dirty_patch_count', 0)
            valid_patch_count = getattr(app_instance, '_last_valid_patch_count', 0)
            nopanel_patch_count = getattr(app_instance, '_last_nopanel_patch_count', 0)
            cnn_active = bool(getattr(app_instance, '_last_cnn_active', label_name.lower() != 'no_panel'))
            panel_detected = bool(getattr(app_instance, '_last_panel_detected', False))
            yolo_clean_faults = list(getattr(app_instance, '_last_yolo_clean_faults', []))
            yolo_crack_faults = list(getattr(app_instance, '_last_yolo_crack_faults', []))
            clean_count = getattr(app_instance, 'cleaning_count', 0)
            min_valid_patches = APP_CONFIG.get('MIN_VALID_PATCHES', 10)
            
            # Grayscale + overlay (tá»‘i Æ°u: dÃ¹ng LUT thay vÃ¬ putText náº·ng)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            disp = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            # Status â€” chá»‰ tÃ­nh khi label Ä‘á»•i
            label_lower = label_name.lower()
            last_label = label_lower
            if yolo_crack_faults:
                status_text = 'Canh bao nut vo tam pin'
                status_color = 'danger'
                text_color = (0, 0, 255)
            elif not cnn_active:
                status_color = 'warning'
                text_color = (0, 255, 255)
                status_text = 'Panel-Seg: no panel'
            elif valid_patch_count < min_valid_patches:
                status_color = 'warning'
                text_color = (0, 255, 255)
                status_text = 'Low panel coverage'
            elif trigger_class in label_lower:
                status_text = 'Can ve sinh'
                status_color = 'danger'
                text_color = (0, 0, 255)
            else:
                status_text = 'Sach'
                status_color = 'success'
                text_color = (0, 255, 0)
            
            # Text overlay â€” minimal (chá»‰ thÃ´ng tin cáº§n thiáº¿t)
            cv2.putText(disp, f"Loai: {label_name}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
            if cnn_active and pred_class >= 0 and len(pred_probs) > pred_class:
                cv2.putText(disp, f"Conf: {pred_probs[pred_class]*100:.0f}%", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
            cv2.putText(disp, f"Patch ban: {area_ratio*100:.0f}% ({dirty_patch_count}/{valid_patch_count})", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            # PRE-ENCODE JPEG 1 Láº¦N (video_feed dÃ¹ng láº¡i, khÃ´ng encode láº¡i)
            ret, buffer = cv2.imencode('.jpg', disp, encode_params)
            cnn_patch_frame = getattr(app_instance, '_last_cnn_patch_frame', None)
            yolo_panel_frame = getattr(app_instance, '_last_yolo_panel_frame', None)
            cnn_ret, cnn_buffer = (False, None)
            yolo_ret, yolo_buffer = (False, None)
            if cnn_patch_frame is not None:
                cnn_ret, cnn_buffer = cv2.imencode('.jpg', cnn_patch_frame, encode_params)
            if yolo_panel_frame is not None:
                yolo_ret, yolo_buffer = cv2.imencode('.jpg', yolo_panel_frame, encode_params)

            # FPS

            elapsed = now - start_time

            fps = frame_count / elapsed if elapsed > 0 else 0


            # Snapshot info (chá»‰ tÃ­nh khi cÃ³ thay Ä‘á»•i)

            snapshot_path = getattr(app_instance, '_last_snapshot_filename', None)

            snapshot_time_str = getattr(app_instance, '_last_snapshot_time', None)


            next_snapshot = 0

            snapshot_ts = getattr(app_instance, '_last_snapshot_timestamp', None)

            if snapshot_ts:

                interval = APP_CONFIG.get('SNAPSHOT_INTERVAL', CONFIG.get('SNAPSHOT_INTERVAL', 600))

                next_snapshot = max(0, int(interval - (now - snapshot_ts)))


            # PLC status

            plc = getattr(app_instance, 'plc', None)

            plc_connected = getattr(plc, 'is_connected', False) if plc else False

            plc_ip = _get_plc_ip(APP_CONFIG)
            plc_status_text = f"Connected to {plc_ip}" if plc_connected else 'Not Connected'

            # Update global state + pre-encoded bytes

            with lock:

                current_frame = disp
                if ret:
                    current_frame_bytes = buffer.tobytes()
                if cnn_ret:
                    current_cnn_patch_bytes = cnn_buffer.tobytes()
                if yolo_ret:
                    current_yolo_panel_bytes = yolo_buffer.tobytes()
                current_results['p_dirty'] = float(p_dirty)
                current_results['area_ratio'] = float(area_ratio)
                current_results['predicted_class'] = int(pred_class)
                current_results['label_name'] = label_name

                current_results['pred_probs'] = _cnn_probs_2class(pred_probs)
                current_results['class_names'] = ['sach', 'ban']
                current_results['model_pipeline'] = 'CNN 2-class + YOLO/Panel-Seg auxiliaries'
                current_results['status'] = status_text
                current_results['status_color'] = status_color
                current_results['timestamp'] = now
                current_results['fps'] = fps
                current_results['clean_count'] = clean_count
                current_results['plc_connected'] = plc_connected
                current_results['plc_status'] = plc_status_text
                current_results['confidence'] = float(confidence)
                current_results['dirty_patch_count'] = int(dirty_patch_count)
                current_results['valid_patch_count'] = int(valid_patch_count)
                current_results['nopanel_patch_count'] = int(nopanel_patch_count)
                current_results['cnn_active'] = bool(cnn_active)
                current_results['panel_detected'] = bool(panel_detected)
                current_results['yolo_clean_faults'] = yolo_clean_faults
                current_results['yolo_crack_faults'] = yolo_crack_faults
                current_results['last_snapshot_path'] = snapshot_path
                current_results['last_snapshot_time'] = snapshot_time_str

                current_results['next_snapshot'] = next_snapshot

                current_results['snapshot_interval'] = APP_CONFIG.get('SNAPSHOT_INTERVAL', CONFIG.get('SNAPSHOT_INTERVAL', 600))

                # Sync ALL settings from Desktop App â†’ Web

                current_results['dirt_threshold'] = APP_CONFIG.get('DIRT_AREA_THRESHOLD', CONFIG.get('DIRT_AREA_THRESHOLD', 0.0))

                current_results['camera_id'] = APP_CONFIG.get('CAMERA_ID', CONFIG.get('CAMERA_ID', 0))

                current_results['is_running'] = getattr(app_instance, 'is_running', False)

                current_results['min_confidence'] = APP_CONFIG.get('MIN_CONFIDENCE', CONFIG.get('MIN_CONFIDENCE', 0.6))

                current_results['cnn_dirty_threshold'] = APP_CONFIG.get('CNN_DIRTY_THRESHOLD', CONFIG.get('CNN_DIRTY_THRESHOLD', 0.65))

                current_results['plc_ip'] = plc_ip

                # PZEM-017 Power data
                if hasattr(app_instance, 'power_monitor') and app_instance.power_monitor:
                    pm = app_instance.power_monitor
                    current_results['power_voltage'] = pm.current.get('voltage', 0)
                    current_results['power_current'] = pm.current.get('current', 0)
                    current_results['power_watts'] = pm.current.get('power', 0)
                    current_results['power_energy'] = pm.current.get('energy', 0)
                if hasattr(app_instance, 'efficiency_tracker') and app_instance.efficiency_tracker:
                    et = app_instance.efficiency_tracker
                    ev = et.get_last_event()
                    if ev:
                        current_results['last_efficiency'] = {
                            'pre_power': ev.get('pre_clean_power', 0),
                            'post_power': ev.get('post_clean_power', 0),
                            'gain': ev.get('power_gain', 0),
                            'improvement_pct': ev.get('improvement_pct', 0),
                        }
            
            # 20fps Ä‘á»§ cho giÃ¡m sÃ¡t (giáº£m CPU 40%)
            time.sleep(0.05)
            
        except Exception as e:
            print(f"âŒ Web frame capture error: {e}")
            traceback.print_exc()
            time.sleep(1)


# ==================== FASTAPI ROUTES ====================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, username: str = Depends(verify_credentials)):
    """Trang chá»§"""
    response = templates.TemplateResponse("web_monitor_fastapi.html", {"request": request})
    # KhÃ´ng cache HTML â†’ luÃ´n láº¥y phiÃªn báº£n má»›i nháº¥t
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.get("/video_feed")
async def video_feed(username: str = Depends(verify_credentials)):
    """Video streaming - MJPEG (dÃ¹ng pre-encoded bytes, KHÃ”NG re-encode)"""
    async def generate():
        last_bytes = None
        while True:
            with lock:
                frame_bytes = current_frame_bytes
            
            if frame_bytes is None:
                await asyncio.sleep(0.1)
                continue
            
            # Chá»‰ yield khi frame thá»±c sá»± Ä‘á»•i (trÃ¡nh gá»­i trÃ¹ng)
            if frame_bytes is not last_bytes:
                last_bytes = frame_bytes
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            await asyncio.sleep(0.05)  # 20fps khá»›p vá»›i capture
    
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")
@app.get("/api/current_frame")
async def api_current_frame(username: str = Depends(verify_credentials)):
    """Trả về frame hiện tại dạng JPEG đơn (cho Flutter mobile app)"""
    from starlette.responses import Response
    with lock:
        frame_bytes = current_frame_bytes
    if frame_bytes is None:
        raise HTTPException(status_code=503, detail="No frame available")
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

@app.get("/api/cnn_patch_frame")
async def api_cnn_patch_frame(username: str = Depends(verify_credentials)):
    """Latest CNN 32-patch visualization."""
    from starlette.responses import Response
    with lock:
        frame_bytes = current_cnn_patch_bytes
    if frame_bytes is None:
        raise HTTPException(status_code=503, detail="No CNN patch frame available")
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )

@app.get("/api/yolo_panel_frame")
async def api_yolo_panel_frame(username: str = Depends(verify_credentials)):
    """Latest YOLO/Panel-Seg visualization."""
    from starlette.responses import Response
    with lock:
        frame_bytes = current_yolo_panel_bytes
    if frame_bytes is None:
        raise HTTPException(status_code=503, detail="No YOLO/Panel-Seg frame available")
    return Response(
        content=frame_bytes,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@app.get("/api/status")
async def api_status(username: str = Depends(verify_credentials)):
    """API trạng thái - CÙNG FORMAT với Flask version (tương thích HTML cũ)"""
    with lock:
        results = current_results.copy()
    return JSONResponse(content=results)


@app.get("/api/settings")
async def api_get_settings(username: str = Depends(verify_credentials)):
    """Lấy cấu hình hiện tại — đọc từ Desktop APP_CONFIG_REF (reference gốc)"""
    _cfg = APP_CONFIG_REF if APP_CONFIG_REF is not None else CONFIG
    return JSONResponse(content={
        'CAMERA_ID': _cfg.get('CAMERA_ID', CONFIG['CAMERA_ID']),
        'PLC_IP': _get_plc_ip(_cfg),
        'DIRT_THRESHOLD': _cfg.get('DIRT_AREA_THRESHOLD', CONFIG.get('DIRT_AREA_THRESHOLD', 0.0)),
        'SNAPSHOT_INTERVAL': _cfg.get('SNAPSHOT_INTERVAL', CONFIG['SNAPSHOT_INTERVAL']),
        'TRIGGER_CLASS': _cfg.get('TRIGGER_CLASS', CONFIG['TRIGGER_CLASS']),
        'MIN_CONFIDENCE': _cfg.get('MIN_CONFIDENCE', CONFIG['MIN_CONFIDENCE']),
        'CNN_DIRTY_THRESHOLD': _cfg.get('CNN_DIRTY_THRESHOLD', CONFIG.get('CNN_DIRTY_THRESHOLD', 0.65)),
        'IS_RUNNING': getattr(app_instance, 'is_running', False) if app_instance else False,
    })


@app.post("/api/settings")
async def api_post_settings(request: Request, username: str = Depends(verify_credentials)):
    """Cập nhật cấu hình từ xa"""
    data = await request.json()
    
    # Dùng APP_CONFIG_REF trực tiếp (reference gốc đến CONFIG của __main__)
    _cfg = APP_CONFIG_REF if APP_CONFIG_REF is not None else CONFIG
    
    if 'CAMERA_ID' in data:
        new_camera_id = int(data['CAMERA_ID'])
        CONFIG['CAMERA_ID'] = new_camera_id
        _cfg['CAMERA_ID'] = new_camera_id
        with lock:
            current_results['camera_id'] = new_camera_id
        if app_instance is not None:
            command_queue.put(('camera', new_camera_id))
            print(f"[OK] CAMERA_ID command queued: {new_camera_id}")
    
    if 'DIRT_THRESHOLD' in data:
        new_threshold = float(data['DIRT_THRESHOLD'])
        CONFIG['DIRT_AREA_THRESHOLD'] = new_threshold
        CONFIG['DIRT_THRESHOLD'] = new_threshold
        _cfg['DIRT_AREA_THRESHOLD'] = new_threshold
        with lock:
            current_results['dirt_threshold'] = new_threshold
        if app_instance is not None:
            command_queue.put(('threshold', new_threshold))
            print(f"[OK] DIRT_THRESHOLD command queued: {new_threshold*100:.1f}%")

    if 'CNN_DIRTY_THRESHOLD' in data:
        new_cnn_threshold = float(data['CNN_DIRTY_THRESHOLD'])
        CONFIG['CNN_DIRTY_THRESHOLD'] = new_cnn_threshold
        _cfg['CNN_DIRTY_THRESHOLD'] = new_cnn_threshold
        with lock:
            current_results['cnn_dirty_threshold'] = new_cnn_threshold
        if app_instance is not None:
            command_queue.put(('cnn_dirty_threshold', new_cnn_threshold))
            print(f"[OK] CNN_DIRTY_THRESHOLD command queued: {new_cnn_threshold:.2f}")

    if 'PLC_IP' in data:
        new_plc_ip = str(data['PLC_IP'])
        _set_plc_ip(_cfg, new_plc_ip)
        with lock:
            current_results['plc_ip'] = new_plc_ip
        if app_instance is not None:
            command_queue.put(('plc_ip_update', new_plc_ip))

    return JSONResponse(content={'success': True, 'config': CONFIG})
@app.post("/api/plc/reconnect")

async def api_plc_reconnect(request: Request, username: str = Depends(verify_credentials)):

    """Káº¿t ná»‘i láº¡i PLC"""

    data = await request.json()
    _cfg = APP_CONFIG_REF if APP_CONFIG_REF is not None else CONFIG
    if 'PLC_IP' in data:
        _set_plc_ip(_cfg, str(data['PLC_IP']))
    if app_instance is not None:
        plc_ip = _get_plc_ip(_cfg)
        command_queue.put(('plc_reconnect', plc_ip))
        return JSONResponse(content={'success': True, 'message': f'ÄÃ£ gá»­i lá»‡nh káº¿t ná»‘i PLC {plc_ip}'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App khÃ´ng hoáº¡t Ä‘á»™ng'})


@app.post("/api/plc/manual_clean")
async def api_manual_clean(username: str = Depends(verify_credentials)):
    """Vá»‡ sinh thá»§ cÃ´ng - kÃ­ch PLC tá»« xa"""
    if app_instance is not None:
        command_queue.put(('manual_clean', True))
        print("ðŸ§¹ Manual cleaning command queued from Web (FastAPI)")
        return JSONResponse(content={'success': True, 'message': 'ÄÃ£ gá»­i lá»‡nh vá»‡ sinh thá»§ cÃ´ng'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App khÃ´ng hoáº¡t Ä‘á»™ng'})


@app.get("/api/closed_loop/status")
async def api_closed_loop_status():
    """Lấy trạng thái chu trình khép kín"""
    if app_instance is not None and getattr(app_instance, 'closed_loop_engine', None) is not None:
        return JSONResponse(content={'success': True, 'data': app_instance.closed_loop_engine.get_status_dict()})
    return JSONResponse(content={'success': False, 'message': 'Closed-loop engine chưa sẵn sàng'})


@app.post("/api/closed_loop/trigger")
async def api_closed_loop_trigger(username: str = Depends(verify_credentials)):
    """Kích hoạt chu trình khép kín từ xa qua Web/Mobile"""
    if app_instance is not None:
        command_queue.put(('closed_loop_trigger', True))
        return JSONResponse(content={'success': True, 'message': 'Đã gửi lệnh kích hoạt Chu trình khép kín'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App không hoạt động'})


@app.post("/api/closed_loop/cancel")
async def api_closed_loop_cancel(username: str = Depends(verify_credentials)):
    """Hủy chu trình khép kín từ xa"""
    if app_instance is not None:
        command_queue.put(('closed_loop_cancel', True))
        return JSONResponse(content={'success': True, 'message': 'Đã gửi lệnh hủy Chu trình khép kín'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App không hoạt động'})


@app.post("/api/snapshot_interval")
async def api_snapshot_interval(request: Request, username: str = Depends(verify_credentials)):
    """Thay Ä‘á»•i chu ká»³ chá»¥p áº£nh"""
    data = await request.json()
    if 'interval' not in data:
        return JSONResponse(content={'success': False, 'message': 'Thiáº¿u tham sá»‘ interval'}, status_code=400)
    
    interval_seconds = int(data['interval'])
    if interval_seconds < 60 or interval_seconds > 86400:
        return JSONResponse(content={'success': False, 'message': 'Chu ká»³ pháº£i 60-86400 giÃ¢y'}, status_code=400)
    
    CONFIG['SNAPSHOT_INTERVAL'] = interval_seconds
    # Cáº­p nháº­t trá»±c tiáº¿p desktop CONFIG gá»‘c qua reference
    if APP_CONFIG_REF is not None:
        APP_CONFIG_REF['SNAPSHOT_INTERVAL'] = interval_seconds
    with lock:
        current_results['snapshot_interval'] = interval_seconds
    if app_instance is not None:
        command_queue.put(('snapshot_interval', interval_seconds))
        print(f"âœ… SNAPSHOT_INTERVAL queued: {interval_seconds}s ({interval_seconds//60} phÃºt)")
    
    return JSONResponse(content={
        'success': True,
        'message': f'ÄÃ£ cáº­p nháº­t chu ká»³: {interval_seconds // 60} phÃºt',
        'interval': interval_seconds
    })


@app.post("/api/system/start")
async def api_system_start(username: str = Depends(verify_credentials)):
    """Báº¯t Ä‘áº§u giÃ¡m sÃ¡t tá»« Web"""
    if app_instance is not None:
        command_queue.put(('system_start', True))
        return JSONResponse(content={'success': True, 'message': 'ÄÃ£ gá»­i lá»‡nh Báº®T Äáº¦U'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App khÃ´ng hoáº¡t Ä‘á»™ng'})


@app.post("/api/system/stop")
async def api_system_stop(username: str = Depends(verify_credentials)):
    """Dá»«ng giÃ¡m sÃ¡t tá»« Web"""
    if app_instance is not None:
        command_queue.put(('system_stop', True))
        return JSONResponse(content={'success': True, 'message': 'ÄÃ£ gá»­i lá»‡nh Dá»ªNG'})
    return JSONResponse(content={'success': False, 'message': 'Desktop App khÃ´ng hoáº¡t Ä‘á»™ng'})

# ==================== POWER MONITORING API ====================
@app.get("/api/power")
async def api_power(username: str = Depends(verify_credentials)):
    """Current DC power data from PZEM-017"""
    with lock:
        return JSONResponse(content={
            'voltage': current_results.get('power_voltage', 0),
            'current': current_results.get('power_current', 0),
            'power': current_results.get('power_watts', 0),
            'energy': current_results.get('power_energy', 0),
            'efficiency': current_results.get('last_efficiency'),
        })

@app.get("/api/power/history")
async def api_power_history(hours: int = 1, username: str = Depends(verify_credentials)):
    """Lich su power readings trong N gio gan nhat"""
    try:
        from power_db import get_power_history
        data = get_power_history(hours=min(hours, 168))  # Max 7 days
        return JSONResponse(content={'readings': data})
    except Exception as e:
        return JSONResponse(content={'readings': [], 'error': str(e)})

@app.get("/api/power/hourly")
async def api_power_hourly(username: str = Depends(verify_credentials)):
    """Hourly power average and energy stats"""
    try:
        from power_db import get_hourly_stats
        data = get_hourly_stats()
        return JSONResponse(content={'hourly': data})
    except Exception as e:
        return JSONResponse(content={'hourly': [], 'error': str(e)})

@app.get("/api/power/daily")
async def api_power_daily(days: int = 7, username: str = Depends(verify_credentials)):
    """Daily energy stats"""
    try:
        from power_db import get_daily_stats
        data = get_daily_stats(days=min(days, 90))  # Max 3 months
        return JSONResponse(content={'daily': data})
    except Exception as e:
        return JSONResponse(content={'daily': [], 'error': str(e)})

@app.get("/api/power/monthly")
async def api_power_monthly(username: str = Depends(verify_credentials)):
    """Monthly energy stats"""
    try:
        from power_db import get_monthly_stats
        data = get_monthly_stats()
        return JSONResponse(content={'monthly': data})
    except Exception as e:
        return JSONResponse(content={'monthly': [], 'error': str(e)})

@app.get("/api/power/export")
async def api_power_export(username: str = Depends(verify_credentials)):
    """Export power data to CSV"""
    try:
        from power_db import generate_readings_csv_rows
        from fastapi.responses import StreamingResponse
        headers = {
            'Content-Disposition': 'attachment; filename="pzem_power_history.csv"',
            'Content-Type': 'text/csv; charset=utf-8'
        }
        return StreamingResponse(generate_readings_csv_rows(), headers=headers)
    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)})

@app.get("/api/power/export-json")
async def api_power_export_json(username: str = Depends(verify_credentials)):
    """Export power data to JSON file"""
    try:
        from power_db import get_db
        import json
        
        async def json_generator():
            yield "["
            first = True
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, voltage, current, power, energy FROM power_readings ORDER BY timestamp DESC")
                while True:
                    row = cursor.fetchone()
                    if not row:
                        break
                    record = {
                        'timestamp': row['timestamp'],
                        'voltage': row['voltage'],
                        'current': row['current'],
                        'power': row['power'],
                        'energy': row['energy']
                    }
                    chunk = ""
                    if not first:
                        chunk += ","
                    first = False
                    chunk += json.dumps(record, ensure_ascii=False)
                    yield chunk
            yield "]"
            
        from fastapi.responses import StreamingResponse
        headers = {
            'Content-Disposition': 'attachment; filename="pzem_power_history.json"',
            'Content-Type': 'application/json; charset=utf-8'
        }
        return StreamingResponse(json_generator(), headers=headers)
    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)})

@app.get("/api/cleaning/efficiency")
async def api_cleaning_efficiency(limit: int = 20, username: str = Depends(verify_credentials)):
    """List of cleaning events with pre/post power"""
    try:
        from power_db import get_cleaning_events
        events = get_cleaning_events(limit=min(limit, 100))
        return JSONResponse(content={'events': events})
    except Exception as e:
        return JSONResponse(content={'events': [], 'error': str(e)})


# ==================== LOCAL AI CHATBOT API (Ollama qwen2.5:0.5b) ====================
@app.get("/api/ai/status")
async def api_ai_status(username: str = Depends(verify_credentials)):
    """Kiểm tra trạng thái kết nối Ollama local và model qwen2.5:0.5b"""
    try:
        from ai_assistant import ai_engine
        is_online, msg = ai_engine.check_ollama()
        models = ai_engine.get_installed_models() if is_online else []
        return JSONResponse(content={
            'online': is_online,
            'message': msg,
            'model': ai_engine.model,
            'installed_models': models
        })
    except Exception as e:
        return JSONResponse(content={'online': False, 'message': str(e), 'model': 'qwen2.5:0.5b'})


@app.post("/api/ai/chat")
async def api_ai_chat(request: Request, username: str = Depends(verify_credentials)):
    """
    Endpoint Chat AI dành cho Web Monitor và App Mobile React Native.
    - Nhận tin nhắn: {"message": "..."}
    - Đọc thông số hệ thống thời gian thực đưa vào bối cảnh
    - Tự động thực thi lệnh nếu phát hiện ý định (vệ sinh, khởi động, dừng, kết nối PLC)
    """
    try:
        data = await request.json()
        user_message = str(data.get('message', '')).strip()
        if not user_message:
            return JSONResponse(content={'success': False, 'message': 'Tin nhắn không được để trống'}, status_code=400)

        from ai_assistant import ai_engine
        
        with lock:
            res_snapshot = current_results.copy()

        # Gọi AI Engine xử lý chat & thực thi lệnh ngầm nếu có
        ai_res = ai_engine.chat(user_message, current_results=res_snapshot, command_queue=command_queue)

        return JSONResponse(content={
            'success': True,
            'reply': ai_res.get('reply', ''),
            'action': ai_res.get('action'),
            'model': ai_res.get('model', 'qwen2.5:0.5b')
        })
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': f'Lỗi xử lý AI: {str(e)}'}, status_code=500)


# ==================== ZALO BOT & SMART ALERTS API ====================
@app.get("/api/zalo/status")
async def api_zalo_status(username: str = Depends(verify_credentials)):
    """Lấy trạng thái hoạt động của Zalo Bot"""
    try:
        from zalo_service import zalo_service
        status = zalo_service.get_status()
        return JSONResponse(content={'success': True, 'data': status})
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': str(e)}, status_code=500)


@app.get("/api/zalo/config")
async def api_zalo_get_config(username: str = Depends(verify_credentials)):
    """Lấy cấu hình Zalo Bot hiện tại"""
    try:
        from zalo_service import zalo_service
        return JSONResponse(content={'success': True, 'config': zalo_service.config})
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': str(e)}, status_code=500)


@app.post("/api/zalo/config")
async def api_zalo_set_config(request: Request, username: str = Depends(verify_credentials)):
    """Cập nhật cấu hình Zalo Bot (Token, Chat ID, Cooldown, Bật/Tắt)"""
    try:
        data = await request.json()
        from zalo_service import zalo_service
        zalo_service.update_config(data)
        return JSONResponse(content={'success': True, 'message': 'Đã cập nhật cấu hình Zalo Bot!', 'config': zalo_service.config})
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': f'Lỗi cập nhật: {str(e)}'}, status_code=500)


@app.post("/api/zalo/test_alert")
async def api_zalo_test_alert(request: Request, username: str = Depends(verify_credentials)):
    """Gửi tin nhắn cảnh báo thử nghiệm tới danh sách Admin Chat ID"""
    try:
        from zalo_service import zalo_service
        chat_ids = zalo_service.config.get('admin_chat_ids', [])
        if not chat_ids:
            return JSONResponse(content={
                'success': False,
                'message': 'Chưa có Chat ID nào được đăng ký! Vui lòng chat /start với Bot trên Zalo trước hoặc nhập Chat ID vào cài đặt.'
            }, status_code=400)

        test_msg = (
            " **[THỬ NGHIỆM]: KẾT NỐI HỆ THỐNG CẢNH BÁO ZALO THÀNH CÔNG!** \n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            " **Hệ thống:** Giám sát & Vệ sinh Tấm Pin Mặt Trời AI (SolarClean)\n"
            f" **Thời gian gửi:** {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}\n"
            " **Tính năng kích hoạt:**\n"
            " • Cảnh báo bụi bẩn & vật cản (lá cây, phân chim)\n"
            " • Chatbot hỏi đáp 2 chiều kết nối AI Ollama (qwen2.5:0.5b)\n"
            " • Điều khiển PLC vệ sinh từ xa qua Zalo\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            " Gõ `/status` để xem trạng thái hệ thống ngay bây giờ."
        )
        # Gửi không qua cooldown để test tức thời
        sent = zalo_service.send_broadcast_message(test_msg, alert_key=None)
        return JSONResponse(content={'success': True, 'message': f'Đã phát lệnh gửi cảnh báo thử nghiệm tới {len(chat_ids)} người nhận!'})
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': f'Lỗi gửi tin thử nghiệm: {str(e)}'}, status_code=500)


@app.post("/api/zalo/restart")
async def api_zalo_restart(username: str = Depends(verify_credentials)):
    """Khởi động lại Zalo Bot Polling"""
    try:
        from zalo_service import zalo_service
        zalo_service.restart()
        return JSONResponse(content={'success': True, 'message': 'Đã khởi động lại Zalo Bot!'})
    except Exception as e:
        return JSONResponse(content={'success': False, 'message': str(e)}, status_code=500)




@app.get("/snapshots/{filename}")
async def serve_snapshot(filename: str, username: str = Depends(verify_credentials)):
    """Serve snapshot images - CÃ“ AUTH + cháº·n path traversal"""
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    snapshot_dir = Path(_RUNTIME_DIR) / 'snapshots'
    file_path = snapshot_dir / filename


    if file_path.exists() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:

        return FileResponse(str(file_path))

    raise HTTPException(status_code=404, detail="Snapshot not found")



@app.get("/static/{filename}")

async def serve_static(filename: str):

    """Serve static files - CHá»ˆ FILE TRONG WHITELIST (cháº·n lá»™ source code)"""

    if '..' in filename or '/' in filename or '\\' in filename:

        raise HTTPException(status_code=403, detail="Forbidden")


    if filename not in ALLOWED_STATIC_FILES:

        raise HTTPException(status_code=403, detail="File not allowed")


    file_path = Path(_base_dir) / filename
    if file_path.exists():
        return FileResponse(str(file_path))
    raise HTTPException(status_code=404, detail="File not found")


# ==================== WEBSOCKET ====================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket real-time push.
    Server push status mỗi giây -> client không cần polling.
    Client cũng có thể gửi lệnh qua WebSocket.
    """
    # Auth check via cookie
    token = websocket.cookies.get('session')
    if not _get_active_session(token):
        try:
            await websocket.close(code=1008, reason='Not authenticated')
        except Exception:
            pass
        return

    await ws_manager.connect(websocket)
    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            # Push status nhanh (0.3s)
            with lock:
                data = current_results.copy()
            
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(data)
            
            # Lắng nghe lệnh từ client (timeout ngắn -> push nhanh hơn)
            try:
                client_data = await asyncio.wait_for(websocket.receive_json(), timeout=0.3)
                if 'command' in client_data:
                    cmd = client_data['command']
                    value = client_data.get('value', None)
                    command_queue.put((cmd, value))
                    print(f"[CMD] WS command: {cmd} = {value}")
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass
                
    except (WebSocketDisconnect, RuntimeError):
        ws_manager.disconnect(websocket)
    except Exception as e:
        err_msg = str(e).lower()
        if "websocket.close" not in err_msg and "response already completed" not in err_msg:
            print(f"WebSocket notice: {e}")
        ws_manager.disconnect(websocket)



# ==================== LIFECYCLE ====================
@app.on_event("startup")
async def startup_event():
    print("[OK] FastAPI server started")
    print(f"    http://localhost:{CONFIG['WEB_PORT']}")
    print(f"    API docs: http://localhost:{CONFIG['WEB_PORT']}/docs")
    
    # Khởi động Zalo Bot Service
    try:
        from zalo_service import zalo_service
        zalo_service.set_system_hooks(lambda: current_results, command_queue)
        if zalo_service.config.get('enabled', True):
            zalo_service.start()
    except Exception as e:
        print(f"[WARN] [Zalo Service Startup]: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global is_running
    is_running = False
    print("âš ï¸  FastAPI server shutting down...")


# ==================== RUN HELPERS ====================
def run_server_thread(host='0.0.0.0', port=5000):
    """Cháº¡y uvicorn trong thread (gá»i tá»« Desktop App)"""
    import uvicorn
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
    except Exception as e:
        print(f"âŒ FastAPI server error: {e}")


def main():
    """Standalone mode"""
    import uvicorn
    print("=" * 60)
    print("ðŸŒž WEB MONITOR - FastAPI Edition v2.4.0")
    print("=" * 60)
    uvicorn.run(app, host=CONFIG['WEB_HOST'], port=CONFIG['WEB_PORT'], log_level="info")


if __name__ == '__main__':
    main()