@echo off
cd /d "%~dp0.."
echo Blindando partidos y aplicando correcciones del Excel...
call backend\.venv\Scripts\activate.bat
python blindar_y_corregir.py
