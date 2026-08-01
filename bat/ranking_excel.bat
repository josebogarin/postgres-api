@echo off
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\ranking_excel.py" > "%~dp0..\ranking_excel_log.txt" 2>&1
type "%~dp0..\ranking_excel_log.txt"
pause
