@echo off
set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set LOG=%DIR%\test2_log.txt
%PYTHON% "%DIR%\test2.py" > "%LOG%" 2>&1
echo.
type "%LOG%"
pause
