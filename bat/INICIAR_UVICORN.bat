@echo off
taskkill /F /IM uvicorn.exe /T 2>nul
timeout /t 2 /nobreak >nul
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
