@echo off
cd /d "C:\proyecto FAST API"
echo === ESTADO DE FASES: bloqueo + finalizados + editables (solo lectura) ===
call backend\.venv\Scripts\python.exe estado_fases.py
echo.
pause
