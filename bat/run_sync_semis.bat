@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Sync API-Football + avanzar bracket (Semis) ===
python sync_semis.py
echo.
pause
