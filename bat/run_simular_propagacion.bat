@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
echo === LIBERTADORES (torneo 1) ===
python simular_propagacion_clubes.py 1
echo.
echo === SUDAMERICANA (torneo 14) ===
python simular_propagacion_clubes.py 14
pause
