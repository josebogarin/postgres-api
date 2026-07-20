@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\python.exe -u analisis_datos.py > analisis_datos_log.txt 2>&1
echo DONE >> analisis_datos_log.txt
