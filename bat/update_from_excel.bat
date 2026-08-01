@echo off
cd /d "%~dp0.."
echo Actualizando BD desde Excel consolidada...
call backend\.venv\Scripts\activate.bat
python update_from_excel.py
