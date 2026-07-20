@echo off
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\python.exe -u recalc_ranking.py > recalc_ranking_log.txt 2>&1
echo DONE >> recalc_ranking_log.txt
