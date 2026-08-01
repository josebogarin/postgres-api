@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python diag_y_sync_p90.py
pause
