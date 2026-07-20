@echo off
REM run_importar_r32.bat
REM Ejecutar en modo DRY RUN (solo verifica):
REM   Doble click en este archivo
REM
REM Para importar los pronosticos R32:
REM   Doble click en run_importar_r32_IMPORT.bat

echo Verificando pronosticos R32 del Excel...
echo.

REM Copiar el Excel a la carpeta del proyecto si no esta ya ahi
IF NOT EXIST "20260628_1600- BEC BUC PRONOSTICOS CONSOLIDADOS 16AVOS.xlsx" (
    echo AVISO: Asegurate de copiar el Excel a esta carpeta:
    echo   20260628_1600- BEC BUC PRONOSTICOS CONSOLIDADOS 16AVOS.xlsx
    echo.
)

"backend\.venv\Scripts\python.exe" "importar_r32_excel.py"

echo.
pause
