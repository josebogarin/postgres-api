@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
python diag_sistema_schema.py
echo.
echo === Listo. Revisa diag_sistema_schema.txt ===
pause
