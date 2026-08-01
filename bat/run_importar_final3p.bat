@echo off
cd /d "%~dp0.."
echo === DRY RUN: importar apuestas FINAL + 3er PUESTO (P103/P104) - no escribe ===
call backend\.venv\Scripts\python.exe importar_apuestas_fase.py final3p
echo.
pause
