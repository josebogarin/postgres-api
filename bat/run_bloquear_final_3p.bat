@echo off
cd /d "%~dp0.."
echo === DRY RUN: ver fases Final/3er puesto (no escribe) ===
call backend\.venv\Scripts\python.exe bloquear_final_3p.py
echo.
pause
