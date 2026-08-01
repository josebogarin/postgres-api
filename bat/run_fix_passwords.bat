@echo off
cd /d "%~dp0.."
echo Diagnosticando y reparando contraseñas en app_db...
echo.
call backend\.venv\Scripts\activate.bat
python fix_passwords_appdb.py
echo.
pause
