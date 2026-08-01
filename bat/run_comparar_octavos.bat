@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate
python comparar_octavos_excel_bd.py
pause
