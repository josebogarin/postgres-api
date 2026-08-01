@echo off
cd /d "%~dp0.."
echo === RANKING ACTUAL (top 20) - solo lectura, directo de puntaje_detalle ===
call backend\.venv\Scripts\python.exe ranking_actual.py
echo.
pause
