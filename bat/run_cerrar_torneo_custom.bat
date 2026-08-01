@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\python.exe cerrar_torneo_custom.py > cerrar_torneo_custom_log.txt 2>&1
echo DONE >> cerrar_torneo_custom_log.txt
