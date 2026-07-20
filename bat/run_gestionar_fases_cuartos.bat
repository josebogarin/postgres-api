@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul
echo === Gestionar fases: Cerrar Octavos / Abrir Cuartos / Calcular ===
python gestionar_fases_cuartos.py
echo.
pause
