@echo off
cd /d "C:\proyecto FAST API"
echo === RANKING ACTUAL (top 20) - solo lectura, directo de puntaje_detalle ===
call backend\.venv\Scripts\python.exe ranking_actual.py
echo.
pause
