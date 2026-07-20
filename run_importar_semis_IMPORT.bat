@echo off
cd /d "C:\proyecto FAST API"
echo === IMPORT REAL: escribe apuestas SEMIFINAL en la BD becbuc ===
call backend\.venv\Scripts\python.exe importar_semis_excel.py --import
echo.
pause
