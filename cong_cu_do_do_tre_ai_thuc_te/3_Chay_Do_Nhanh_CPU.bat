@echo off
cd /d "%~dp0"
title SolarClean - Do Nhanh Do Tre AI tren CPU
echo =========================================================================
echo  SolarClean - Benchmark AI tren CPU (FP32)
echo =========================================================================
echo Dang chay do do tre suy luan AI tren CPU...
echo.

python benchmark_core.py --device cpu --runs 20 --warmup 5
echo.
echo =========================================================================
echo Hoan thanh! Ket qua chi tiet da duoc luu trong 'ket_qua_thuc_nghiem/'
echo =========================================================================
pause
