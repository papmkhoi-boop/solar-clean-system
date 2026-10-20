# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['solar_panel_plc_auto_tflite.py'],
    pathex=[],
    binaries=[('snap7.dll', '.')],
    datas=[
        ('buiban.h5', '.'),
        ('labels_2classes.txt', '.'),
        ('panel 2.pt', '.')
    ],
    hiddenimports=[
        'snap7', 
        'cv2', 
        'PIL', 
        'PIL.ImageTk', 
        'PIL.ImageDraw', 
        'PIL.ImageFont',
        'tensorflow',
        'ultralytics'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'scipy', 'pandas', 'IPython', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'test', 'unittest'],
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
    name='SolarClean_Final',
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
    icon=['SolarClean.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SolarClean_Final'
)
