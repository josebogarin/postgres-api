@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Recalcular puntajes + bloquear cuartos ===
python recalc_octavos_bloquear_cuartos.py
echo.
pause
