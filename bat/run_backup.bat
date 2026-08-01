@echo off
echo Iniciando backup BECBUC...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0..\backup_becbuc.ps1"
pause
