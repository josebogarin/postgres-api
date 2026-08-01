@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === Leyendo URL ngrok (127.0.0.1:4040) ===
python get_ngrok.py
echo.
pause
