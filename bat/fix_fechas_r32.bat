@echo off
echo Corrigiendo fechas R32...
cd /d "%~dp0.."
backend\.venv\Scripts\python.exe fix_fechas_r32.py
pause
