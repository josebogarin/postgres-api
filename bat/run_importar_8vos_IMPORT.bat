@echo off
echo ============================================================
echo  BECBUC - IMPORTAR 8vos + BLOQUEAR R32
echo ============================================================
echo.

SET PYTHON="%~dp0..\backend\.venv\Scripts\python.exe"
SET SCRIPT="%~dp0..\importar_8vos_excel.py"

%PYTHON% %SCRIPT% --import

echo.
pause
