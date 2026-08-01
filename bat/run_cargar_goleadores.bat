@echo off
cd /d "%~dp0.."
echo Cargando tabla de goleadores desde API-Football...
echo.
backend\.venv\Scripts\python.exe cargar_goleadores.py
echo.
pause
