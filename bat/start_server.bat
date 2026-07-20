@echo off
cd /d "C:\proyecto FAST API\backend"
start "BECBUC Server" cmd /k ".venv\Scripts\activate && uvicorn app.main:app --port 8000"
