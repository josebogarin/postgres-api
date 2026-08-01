@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Finalizar P097 (France vs Morocco) + Recalcular puntajes Cuartos ===
python finalizar_p097_y_calcular.py
echo.
pause
