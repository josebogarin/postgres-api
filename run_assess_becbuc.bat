@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate
cd /d "C:\proyecto FAST API"
python -u assess_becbuc_db.py > assess_becbuc_out.txt 2>&1
echo ---- FIN ---- >> assess_becbuc_out.txt
notepad assess_becbuc_out.txt
