@echo off
chcp 65001 >nul
cd /D "%~dp0.."
backend\.venv\Scripts\python.exe -u verificar_p49.py
echo.
type verificar_p49_output.txt
pause
