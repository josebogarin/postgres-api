@echo off
cd /d "C:\proyecto FAST API"
echo Ejecutando sync_paux_a_apuesta.py ...
"C:\proyecto FAST API\backend\.venv\Scripts\python.exe" sync_paux_a_apuesta.py
echo Terminado. Ver resultado_sync_paux.txt
pause
