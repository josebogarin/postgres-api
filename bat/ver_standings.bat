@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python ver_standings.py
