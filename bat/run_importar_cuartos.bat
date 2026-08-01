@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === DRY RUN cuartos (no escribe en BD) ===
python importar_cuartos_excel.py
echo.
pause
