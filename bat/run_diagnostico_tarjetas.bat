@echo off
cd /d "%~dp0..\backend"
.venv\Scripts\python.exe ..\diagnostico_tarjetas_api.py
pause
