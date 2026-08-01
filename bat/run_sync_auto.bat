@echo off
cd /d "%~dp0.."
"%~dp0..\backend\.venv\Scripts\python.exe" "%~dp0..\sync_auto.py"
