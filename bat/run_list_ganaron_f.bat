@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0.."
call backend\.venv\Scripts\activate
python -u list_ganaron_f.py > list_ganaron_f_out.txt 2>&1
echo ---- FIN ---- >> list_ganaron_f_out.txt
notepad list_ganaron_f_out.txt
