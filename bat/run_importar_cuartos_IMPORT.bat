@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul
echo === IMPORTAR cuartos a la BD ===
python importar_cuartos_excel.py --import
echo.
pause
