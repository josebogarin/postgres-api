@echo off
cd /d "%~dp0.."
echo Avanzando bracket y verificando mejores terceros...
call backend\.venv\Scripts\activate.bat
python avanzar_bracket.py
