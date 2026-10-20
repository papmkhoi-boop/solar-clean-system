@echo off
cd /d "%~dp0"
title SolarClean - Do Nhanh Do Tre AI tren GPU (FP16)
echo =========================================================================
echo  SolarClean - Benchmark AI tren GPU (NVIDIA CUDA FP16)
echo =========================================================================
echo Dang chay do do tre suy luan AI tren GPU...
echo.

python benchmark_core.py --device cuda --half --runs 30 --warmup 10
echo.
echo =========================================================================
echo Hoan thanh! Ket qua chi tiet da duoc luu trong 'ket_qua_thuc_nghiem/'
echo =========================================================================
pause
