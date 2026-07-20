@echo off
cd /d "C:\proyecto FAST API"
start "" ngrok.exe http 8000
timeout /t 3 /nobreak >nul
start http://127.0.0.1:4040
