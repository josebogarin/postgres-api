@echo off
set "PYTHON=C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
"%PYTHON%" "C:\proyecto FAST API\auditoria_jugador.py" "gonzalo gimenez" 2 "C:\proyecto FAST API\auditoria_gonzalo_gimenez.xlsx" > "C:\proyecto FAST API\auditoria_gonzalo_log.txt" 2>&1
type "C:\proyecto FAST API\auditoria_gonzalo_log.txt"
pause
