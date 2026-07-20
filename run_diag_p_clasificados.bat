@echo off
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python diag_p_clasificados.py
pause
