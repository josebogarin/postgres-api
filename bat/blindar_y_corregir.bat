@echo off
cd /d "C:\proyecto FAST API"
echo Blindando partidos y aplicando correcciones del Excel...
call backend\.venv\Scripts\activate.bat
python blindar_y_corregir.py
