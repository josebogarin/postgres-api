@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
python fix_sistema_columns.py
echo.
echo === Listo. Ahora reinicia uvicorn ===
pause
