# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None
PROJECT_DIR = os.path.abspath(".")
os.environ["YOLO_AUTOINSTALL"] = "false"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


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

datas = [
    (existing("buiban.h5"), "."),
    (existing("labels_2classes.txt"), "."),
    (existing("panel 2.pt"), "."),
    (existing("Solar.pt"), "."),
    (existing("web_monitor_fastapi.py"), "."),
    (existing("ctut.webp"), "."),
    (existing("templates"), "templates"),
    (existing("taikhoan"), "taikhoan"),
]

a = Analysis(
    [existing("solar_panel_plc_auto_tflite.py")],
    pathex=[PROJECT_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "snap7",
        "snap7.client",
        "snap7.common",
        "snap7.types",
        "cv2",
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "tensorflow",
        "tensorflow.keras",
        "tensorflow.keras.layers",
        "tensorflow.keras.applications",
        "tensorflow.keras.applications.efficientnet",
        "ultralytics",
        "torch",
        "torchvision",
        "web_monitor_fastapi",
        "fastapi",
        "fastapi.middleware.cors",
        "fastapi.responses",
        "fastapi.security",
        "fastapi.templating",
        "uvicorn",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "starlette",
        "starlette.responses",
        "starlette.routing",
        "starlette.templating",
        "anyio",
        "anyio._backends._asyncio",
        "jinja2",
        "multipart",
        "python_multipart",
        "h11",
        "httptools",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "notebook",
        "jupyter",
        "IPython",
        "pytest",
        "sphinx",
        "docutils",
        "tensorboard",
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
    exclude_binaries=True,
    name="SolarClean",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=existing("SolarClean.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SolarClean_Complete",
)
