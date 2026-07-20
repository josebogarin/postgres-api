@echo off
cd /d "C:\proyecto FAST API"
echo === VERIFICAR item P (equipo que pasa) por fase - solo lectura ===
call backend\.venv\Scripts\python.exe verificar_item_p.py
echo.
pause
