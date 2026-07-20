@echo off
cd /d "C:\proyecto FAST API"
echo === IMPORT REAL: escribe apuestas FINAL + 3er PUESTO (P103/P104) en la BD ===
call backend\.venv\Scripts\python.exe importar_apuestas_fase.py final3p --import
echo.
pause
