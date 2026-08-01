@echo off
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
echo Corriendo generar_excel_becbuc.py... > ..\excel_run_output.log 2>&1
python ..\generar_excel_becbuc.py >> ..\excel_run_output.log 2>&1
echo. >> ..\excel_run_output.log
echo EXIT CODE: %ERRORLEVEL% >> ..\excel_run_output.log
echo Listo. >> ..\excel_run_output.log
