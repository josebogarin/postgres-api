@echo off
cd /d "%~dp0.."
echo === ESTADO DE FASES: bloqueo + finalizados + editables (solo lectura) ===
call backend\.venv\Scripts\python.exe estado_fases.py
echo.
pause
