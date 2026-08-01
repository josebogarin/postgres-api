@echo off
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\buscar_usuario.py" --all > "%~dp0..\buscar_log.txt" 2>&1
type "%~dp0..\buscar_log.txt"
pause
