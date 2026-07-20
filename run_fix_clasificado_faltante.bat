@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: detectar KO sin equipo_clasificado_id (incluye P098) - no escribe ===
call backend\.venv\Scripts\python.exe fix_clasificado_faltante.py
echo.
pause
