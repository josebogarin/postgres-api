@echo off
cd /d "%~dp0.."
echo === DRY RUN: importar apuestas SEMIFINAL (no escribe en BD) ===
call backend\.venv\Scripts\python.exe importar_semis_excel.py
echo.
pause
