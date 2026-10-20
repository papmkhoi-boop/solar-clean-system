@echo off
title HMI SCADA - SolarClean Automatic Supervisory Control
cd /d D:\DuAn
echo ============================================================
echo   KHOI DONG HE THONG HMI SOLAR CLEAN (SCADA WINCC STYLE)
echo ============================================================
set "PY_EXE=C:\Users\ACER\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PY_EXE%" (
    "%PY_EXE%" solar_panel_plc_auto_tflite.py
) else (
    python solar_panel_plc_auto_tflite.py
)
if %errorlevel% neq 0 (
    echo.
    echo [CANH BAO] Chuong trinh da dung lai hoac gap su co.
    pause
)
