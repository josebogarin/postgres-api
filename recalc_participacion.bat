@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat
python recalc_participacion.py
pause
