@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: ver fases Final/3er puesto (no escribe) ===
call backend\.venv\Scripts\python.exe bloquear_final_3p.py
echo.
pause
