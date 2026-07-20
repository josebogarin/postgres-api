@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul
echo === Estado Semis / 3er puesto / Final (solo lectura) ===
python estado_semis_bracket.py
echo.
pause
