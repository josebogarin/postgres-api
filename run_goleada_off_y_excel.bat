@echo off
echo === Puntaje Grupos + Mayor Goleada off ===
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat
cd /d "C:\proyecto FAST API"
python goleada_off_y_excel_grupos.py > goleada_log.txt 2>&1
echo Codigo de salida: %ERRORLEVEL% >> goleada_log.txt
echo.
echo Revisa goleada_log.txt para ver el resultado.
pause
