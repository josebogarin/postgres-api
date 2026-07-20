@echo off
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
start "BECBUC-Uvicorn" cmd /k "uvicorn app.main:app --reload --port 8000"
timeout /t 3
start "" "http://localhost:8000/static/BECBUC-portal.html"
