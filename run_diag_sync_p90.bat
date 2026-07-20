@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat
python diag_y_sync_p90.py
pause
