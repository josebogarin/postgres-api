@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: rellenar pred_equipo_clasifica NULL en KO desde Excel corregido (no escribe) ===
call backend\.venv\Scripts\python.exe fill_clasifica_null.py
echo.
pause
