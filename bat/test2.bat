@echo off
set PYTHON="C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
set DIR=C:\proyecto FAST API
set LOG=%DIR%\test2_log.txt
%PYTHON% "%DIR%\test2.py" > "%LOG%" 2>&1
echo.
type "%LOG%"
pause
