@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: diagnostico + correccion item L (VAR) - no escribe ===
call backend\.venv\Scripts\python.exe fix_var_L.py
echo.
pause
