@echo off
cd /d "%~dp0"
title SolarClean - Cai Dat Thu Vien Python
echo =========================================================================
echo  SolarClean - Cai Dat Thu Vien Can Thiet Cho May Tinh Thuc Te
echo =========================================================================
echo Dang cai dat: torch, torchvision, ultralytics, opencv-python, pillow...
echo.

pip install -r requirements.txt
echo.
echo =========================================================================
echo Cai dat hoan tat! Ban co the nhap dup vao '1_Chay_Giao_Dien_Do_Tre.bat'
echo =========================================================================
pause
