@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python comparar_excel_vs_bd.py
pause
