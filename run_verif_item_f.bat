@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate
python -u verif_item_f.py > verif_item_f_out.txt 2>&1
echo ---- FIN ---- >> verif_item_f_out.txt
notepad verif_item_f_out.txt
