@echo off
chcp 65001 >nul
cd /D "C:\proyecto FAST API"
echo Generando Excel de auditoria...
backend\.venv\Scripts\python.exe -u generar_excel_becbuc.py 2 > excel_gen_log.txt 2>&1
echo.
type excel_gen_log.txt
