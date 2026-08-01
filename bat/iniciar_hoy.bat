@echo off
echo Iniciando partidos de hoy...
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
python iniciar_paraguay_usa.py > iniciar_hoy_log.txt 2>&1
echo Codigo: %ERRORLEVEL% >> iniciar_hoy_log.txt
type iniciar_hoy_log.txt
pause
