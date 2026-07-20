@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate
python -u list_cherem_globales.py cherem hs > list_cherem_globales_out.txt 2>&1
echo ---- FIN ---- >> list_cherem_globales_out.txt
notepad list_cherem_globales_out.txt
