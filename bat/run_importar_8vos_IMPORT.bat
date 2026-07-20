@echo off
echo ============================================================
echo  BECBUC - IMPORTAR 8vos + BLOQUEAR R32
echo ============================================================
echo.

SET PYTHON="C:\proyecto FAST API\backend\.venv\Scripts\python.exe"
SET SCRIPT="C:\proyecto FAST API\importar_8vos_excel.py"

%PYTHON% %SCRIPT% --import

echo.
pause
