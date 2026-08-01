@echo off
set "PYTHON=%~dp0..\backend\.venv\Scripts\python.exe"
"%PYTHON%" "%~dp0..\auditoria_jugador.py" "gonzalo gimenez" 2 "%~dp0..\auditoria_gonzalo_gimenez.xlsx" > "%~dp0..\auditoria_gonzalo_log.txt" 2>&1
type "%~dp0..\auditoria_gonzalo_log.txt"
pause
