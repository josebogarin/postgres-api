@echo off
REM run_importar_r32_IMPORT.bat
REM IMPORTA los pronosticos R32 a la BD (escribe en apuesta)

echo Importando pronosticos R32 del Excel a la BD...
echo.

"backend\.venv\Scripts\python.exe" "importar_r32_excel.py" --import

echo.
pause
