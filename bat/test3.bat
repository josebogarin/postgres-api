@echo off
set PYTHON="C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
set DIR=C:\proyecto FAST API
set LOG=%DIR%\test3_log.txt
%PYTHON% "%DIR%\test3.py" > "%LOG%" 2>&1
echo Resultado:
type "%LOG%"
pause
