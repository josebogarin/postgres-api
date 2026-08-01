@echo off
cd /D "%~dp0.."
backend\.venv\Scripts\python.exe test_simple.py
pause
