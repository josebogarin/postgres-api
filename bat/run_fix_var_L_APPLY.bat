@echo off
cd /d "%~dp0.."
echo === APPLY: corrige el item L (VAR) en puntaje_detalle desde datos actuales ===
call backend\.venv\Scripts\python.exe fix_var_L.py --apply
echo.
pause
