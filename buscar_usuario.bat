@echo off
"C:\proyecto FAST API\backend\.venv\Scripts\python.exe" "C:\proyecto FAST API\buscar_usuario.py" %* > "C:\proyecto FAST API\buscar_log.txt" 2>&1
type "C:\proyecto FAST API\buscar_log.txt"
pause
