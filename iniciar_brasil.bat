@echo off
echo Iniciando partido de Brasil...
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python iniciar_brasil.py > iniciar_brasil_log.txt 2>&1
echo Codigo: %ERRORLEVEL% >> iniciar_brasil_log.txt
type iniciar_brasil_log.txt
pause
