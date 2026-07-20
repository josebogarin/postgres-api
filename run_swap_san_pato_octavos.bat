@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
call backend\.venv\Scripts\activate.bat 2>nul
echo === DRY RUN: swap SANBIE ^<-^> PATO en octavos (P089-P096) ===
python swap_apuestas.py sanbie pato 89 96
echo.
pause
