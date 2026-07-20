@echo off
cd /d "C:\proyecto FAST API"
echo === SYNC P103 (Francia-Inglaterra, 3er puesto): finalizar + cargar items ===
echo (correr cuando el partido este terminado en API-Football)
call backend\.venv\Scripts\python.exe sync_partido.py 103
echo.
pause
