@echo off
echo Iniciando partido de Brasil...
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
python iniciar_brasil.py > iniciar_brasil_log.txt 2>&1
echo Codigo: %ERRORLEVEL% >> iniciar_brasil_log.txt
type iniciar_brasil_log.txt
pause
