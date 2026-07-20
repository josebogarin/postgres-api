@echo off
chcp 65001 >nul
cd /D "C:\proyecto FAST API"
echo Ejecutando check_ultimo.py...
backend\.venv\Scripts\python.exe check_ultimo.py > check_ultimo_log.txt 2>&1
echo.
type check_ultimo_log.txt
echo.
echo Log guardado en check_ultimo_log.txt
pause
