@echo off
cd /d "%~dp0.."
backend\.venv\Scripts\python.exe fix_partido_suspension.py > fix_suspension_log.txt 2>&1
type fix_suspension_log.txt
