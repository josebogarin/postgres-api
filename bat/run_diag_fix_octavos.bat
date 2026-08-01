@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate
python diag_y_fix_octavos.py
