@echo off
cd /d "C:\proyecto FAST API"
echo Actualizando BD desde Excel consolidada...
call backend\.venv\Scripts\activate.bat
python update_from_excel.py
