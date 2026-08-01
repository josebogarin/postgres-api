@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python verificar_excel.py
echo Listo. Revisa verificar_excel_log.txt
pause
