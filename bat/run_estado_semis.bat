@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === Estado Semis / 3er puesto / Final (solo lectura) ===
python estado_semis_bracket.py
echo.
pause
