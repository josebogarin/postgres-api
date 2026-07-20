@echo off
cd /d "C:\proyecto FAST API"
echo Diagnosticando partido de Paraguay...
call backend\.venv\Scripts\activate.bat
python fix_paraguay.py
