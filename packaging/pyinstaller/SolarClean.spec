# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Solar Panel Cleaning System

import os
import sys

block_cipher = None
os.environ['YOLO_AUTOINSTALL'] = 'false'

# Đường dẫn project
PROJECT_DIR = os.path.abspath('.')

def existing(path):
    return os.path.join(PROJECT_DIR, path)

binaries = []
for candidate in (
    existing("snap7.dll"),
    existing(os.path.join("venv", "Lib", "site-packages", "snap7", "lib", "snap7.dll")),
    existing(os.path.join(".venv", "Lib", "site-packages", "snap7", "lib", "snap7.dll")),
):
    if os.path.exists(candidate):
        binaries.append((candidate, "."))

a = Analysis(
    [existing('solar_panel_plc_auto_tflite.py')],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=[
        # Model AI
        (existing('buiban.h5'), '.'),
        (existing('panel 2.pt'), '.'),
        (existing('Solar.pt'), '.'),
        # Labels
        (existing('labels_2classes.txt'), '.'),
        # Web server module
        (existing('web_monitor_fastapi.py'), '.'),
        (existing('ctut.webp'), '.'),
        # HTML templates cho web monitor
        (existing('templates'), 'templates'),
        (existing('taikhoan'), 'taikhoan'),
        # Thư mục snapshots (tạo sẵn)
        (existing('snapshots'), 'snapshots'),
    ],
    hiddenimports=[
        # FastAPI & dependencies
        'fastapi',
        'fastapi.applications',
        'fastapi.routing',
        'fastapi.middleware',
        'fastapi.middleware.cors',
        'fastapi.responses',
        'fastapi.requests',
        'fastapi.staticfiles',
        'fastapi.templating',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'starlette',
        'starlette.responses',
        'starlette.routing',
        'starlette.middleware',
        'starlette.requests',
        'starlette.websockets',
        'starlette.templating',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'multipart',
        'python_multipart',
        'jinja2',
        'httptools',
        'dotenv',
        'click',
        'h11',
        # Snap7 PLC
        'snap7',
        'snap7.client',
        'snap7.common',
        'snap7.types',
        # TFLite / TensorFlow
        'tensorflow',
        'tensorflow.lite',
        'tensorflow.lite.python',
        'tensorflow.lite.python.interpreter',
        'keras',
        # OpenCV
        'cv2',
        # Pillow
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        # Web monitor module
        'web_monitor_fastapi',
        # Cloud API Client
        'cloud_api_client',
        # PyTorch & YOLOv8
        'torch',
        'torchvision',
        'ultralytics',
        'matplotlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Loại bỏ những thứ không cần để giảm size
        'scipy',
        'pandas',
        'notebook',
        'jupyter',
        'IPython',
        'pytest',
        'sphinx',
        'docutils',
        'tensorboard',
        'torchaudio',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='SolarClean',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # Ẩn console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=existing('SolarClean.ico'),
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SolarClean',
)


