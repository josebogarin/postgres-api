@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
echo === Leyendo URL ngrok (127.0.0.1:4040) ===
python get_ngrok.py
echo.
pause
