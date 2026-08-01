@echo off
cd /d "%~dp0..\backend"
call .venv\Scripts\activate.bat
cd /d "%~dp0.."
echo === Finalizar partido KO (P90 Marruecos vs Canada u otro) ===
echo El script preguntara el numero del partido, goles y penales si aplica.
echo.
python finalizar_partido_ko.py
pause
