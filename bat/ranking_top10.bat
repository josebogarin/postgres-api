@echo off
chcp 65001 >nul
cd /D "%~dp0.."
backend\.venv\Scripts\python.exe -u ranking_top10.py > ranking_top10_log.txt 2>&1
