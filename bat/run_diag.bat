@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" diag_apuesta.py
echo Listo. Ver resultado_diag_apuesta.txt
pause
