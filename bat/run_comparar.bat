@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat
python comparar_excel_vs_bd.py
pause
