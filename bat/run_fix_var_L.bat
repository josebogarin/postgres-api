@echo off
cd /d "%~dp0.."
echo === DRY RUN: diagnostico + correccion item L (VAR) - no escribe ===
call backend\.venv\Scripts\python.exe fix_var_L.py
echo.
pause
