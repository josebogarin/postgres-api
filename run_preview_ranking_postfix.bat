@echo off
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python preview_ranking_postfix.py
pause
