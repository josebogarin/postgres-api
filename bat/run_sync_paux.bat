@echo off
cd /d "%~dp0.."
echo Ejecutando sync_paux_a_apuesta.py ...
"%~dp0..\backend\.venv\Scripts\python.exe" sync_paux_a_apuesta.py
echo Terminado. Ver resultado_sync_paux.txt
pause
