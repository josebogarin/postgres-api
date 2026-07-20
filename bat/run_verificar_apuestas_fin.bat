@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: verifica apuestas BD vs Excel fin de torneo (NO escribe) ===
call backend\.venv\Scripts\python.exe verificar_apuestas_fin_torneo.py
echo.
pause
