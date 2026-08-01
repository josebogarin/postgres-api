@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Test export pronosticos + completados ===
python test_export_pronos.py
echo.
pause
