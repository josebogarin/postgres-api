@echo off
cd /d "C:\proyecto FAST API"
echo === Eventos crudos (eventos_api) de la final P104 ===
call backend\.venv\Scripts\python.exe diag_eventos.py 104
echo.
pause
