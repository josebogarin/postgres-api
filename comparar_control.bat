@echo off
chcp 65001 >nul
cd /D "C:\proyecto FAST API"
echo Comparando BD vs Excel de control...
backend\.venv\Scripts\python.exe -u comparar_control_excel.py > comparar_control_log.txt 2>&1
echo.
type comparar_control_log.txt
echo.
echo Listo. Resultado en comparar_control_log.txt
pause
