@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Cerrar CUARTOS: verificar items + calcular + bloquear ===
python cerrar_cuartos.py
echo.
pause
