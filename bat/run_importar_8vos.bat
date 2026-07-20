@echo off
echo ============================================================
echo  BECBUC - Importar pronosticos 8vos de final
echo ============================================================

SET PYTHON="C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
SET SCRIPT="C:\proyecto FAST API\importar_8vos_excel.py"

IF "%1"=="--import" (
    echo MODO: IMPORTAR + BLOQUEAR R32
    echo.
    %PYTHON% %SCRIPT% --import
) ELSE (
    echo MODO: DRY RUN (solo verifica, no importa)
    echo Para importar: run_importar_8vos.bat --import
    echo.
    %PYTHON% %SCRIPT%
)

echo.
pause
