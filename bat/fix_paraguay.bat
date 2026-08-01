@echo off
cd /d "%~dp0.."
echo Diagnosticando partido de Paraguay...
call backend\.venv\Scripts\activate.bat
python fix_paraguay.py
