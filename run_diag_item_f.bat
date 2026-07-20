@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate
python -u diag_item_f.py > diag_item_f_out.txt 2>&1
echo ---- FIN ---- >> diag_item_f_out.txt
notepad diag_item_f_out.txt
