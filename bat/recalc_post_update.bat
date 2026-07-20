@echo off
cd /d "C:\proyecto FAST API"
echo Recalculando puntajes post-update Excel...
call backend\.venv\Scripts\activate.bat
python recalcular_puntajes.py
