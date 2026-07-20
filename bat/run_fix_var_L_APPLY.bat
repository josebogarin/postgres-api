@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: corrige el item L (VAR) en puntaje_detalle desde datos actuales ===
call backend\.venv\Scripts\python.exe fix_var_L.py --apply
echo.
pause
