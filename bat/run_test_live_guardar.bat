@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul
echo === Test endpoint live-guardar-apuestas (no escribe apuestas reales) ===
python test_live_guardar.py
echo.
pause
