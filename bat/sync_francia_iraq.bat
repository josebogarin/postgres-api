@echo off
chcp 65001 >nul
cd /D "%~dp0.."
echo Sincronizando Francia vs Iraq desde API-Football + ESPN...
backend\.venv\Scripts\python.exe -u sync_francia_iraq.py > sync_francia_iraq_log.txt 2>&1
type sync_francia_iraq_log.txt
