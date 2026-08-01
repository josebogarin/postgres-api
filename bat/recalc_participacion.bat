@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python recalc_participacion.py
pause
