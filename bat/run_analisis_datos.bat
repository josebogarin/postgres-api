@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\python.exe -u analisis_datos.py > analisis_datos_log.txt 2>&1
echo DONE >> analisis_datos_log.txt
