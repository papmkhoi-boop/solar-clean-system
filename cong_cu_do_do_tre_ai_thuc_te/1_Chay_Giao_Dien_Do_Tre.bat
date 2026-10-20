@echo off
cd /d "%~dp0"
title SolarClean - Giao Dien Do Do Tre AI Thuc Te (GUI)
echo =========================================================================
echo  SolarClean - Empirical AI Latency Benchmark (GUI Edition)
echo =========================================================================
echo Dang khoi dong Giao Dien Do Do Tre AI (Python Tkinter)...
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Khong tim thay Python tren he thong!
    echo Vui long cai dat Python 3.9+ hoac them Python vao bien moi truong PATH.
    echo.
    pause
    exit /b 1
)

python app_gui_do_do_tre.py
if %errorlevel% neq 0 (
    echo.
    echo [THONG BAO] Ung dung da dong hoac co loi xay ra.
)
pause
