@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat 2>nul
echo === APLICAR swap SANBIE ^<-^> PATO en octavos (P089-P096) ===
python swap_apuestas.py sanbie pato 89 96 --apply
echo.
pause
