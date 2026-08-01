@echo off
cd /d "%~dp0.."
echo === DRY RUN: alinear resultados oficiales BD con el Excel (NO escribe) ===
call backend\.venv\Scripts\python.exe sincronizar_resultados_excel.py
echo.
pause
