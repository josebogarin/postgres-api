@echo off
cd /d "%~dp0.."
echo === VERIFICAR item P (equipo que pasa) por fase - solo lectura ===
call backend\.venv\Scripts\python.exe verificar_item_p.py
echo.
pause
