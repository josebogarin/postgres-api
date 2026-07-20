@echo off
cd /d "C:\proyecto FAST API"
echo === Verificar estado final (torneo cerrado + ranking del live) ===
call backend\.venv\Scripts\python.exe verificar_estado_final.py
echo.
pause
