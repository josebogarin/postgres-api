@echo off
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\actualizar_puntajes.py" > "%~dp0..\actualizar_log.txt" 2>&1
type "%~dp0..\actualizar_log.txt"
pause
