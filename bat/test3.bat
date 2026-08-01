@echo off
set PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
set DIR=%~dp0..
set LOG=%DIR%\test3_log.txt
%PYTHON% "%DIR%\test3.py" > "%LOG%" 2>&1
echo Resultado:
type "%LOG%"
pause
