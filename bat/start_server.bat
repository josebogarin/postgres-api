@echo off
cd /d "%~dp0..\backend"
start "BECBUC Server" cmd /k ".venv\Scripts\activate && uvicorn app.main:app --port 8000"
