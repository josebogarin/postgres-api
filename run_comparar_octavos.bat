@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate
python comparar_octavos_excel_bd.py
pause
