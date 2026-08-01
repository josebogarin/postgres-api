@echo off
cd /d "%~dp0.."
backend\.venv\Scripts\python.exe fix_estado_partido.py 79
pause
