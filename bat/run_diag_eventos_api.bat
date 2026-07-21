@echo off
cd /d "C:\proyecto FAST API"
echo === Consulta EN VIVO a API-Football de la final P104 (1 llamada de cuota) ===
call backend\.venv\Scripts\python.exe diag_eventos_api.py 104
echo.
pause
