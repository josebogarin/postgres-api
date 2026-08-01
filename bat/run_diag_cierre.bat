@echo off
cd /d "%~dp0.."
call backend\.venv\Scripts\python.exe diag_cierre.py > diag_cierre_log.txt 2>&1
echo DONE >> diag_cierre_log.txt
