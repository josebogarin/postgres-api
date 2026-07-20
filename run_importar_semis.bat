@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: importar apuestas SEMIFINAL (no escribe en BD) ===
call backend\.venv\Scripts\python.exe importar_semis_excel.py
echo.
pause
