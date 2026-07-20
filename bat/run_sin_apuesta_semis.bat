@echo off
cd /d "C:\proyecto FAST API"
echo === Quien NO aposto en SEMIFINAL (P101-P102) ===
call backend\.venv\Scripts\python.exe sin_apuesta_semis.py
echo.
pause
