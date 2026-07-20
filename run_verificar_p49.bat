@echo off
chcp 65001 >nul
cd /D "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe -u verificar_p49.py
echo.
type verificar_p49_output.txt
pause
