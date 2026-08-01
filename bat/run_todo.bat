@echo off
cd /d "%~dp0.."
powershell.exe -ExecutionPolicy Bypass -File "run_todo.ps1"
pause
