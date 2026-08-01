@echo off
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
python preview_ranking_postfix.py
pause
