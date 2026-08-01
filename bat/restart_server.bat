@echo off
echo Deteniendo uvicorn anterior...
taskkill /F /IM uvicorn.exe 2>nul
timeout /t 2 /nobreak >nul
echo Iniciando uvicorn con --reload...
cd /d "%~dp0..\backend"
start "BECBUC Server" cmd /k ".venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
echo Listo.
