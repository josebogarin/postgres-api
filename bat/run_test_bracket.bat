@echo off
echo ============================================================
echo  BECBUC - Test Propagacion Bracket KO
echo ============================================================
echo.
echo ATENCION: Este test sobreescribe los resultados KO en la BD.
echo Solo usar en ambiente de pruebas.
echo.
echo Presiona Ctrl+C para cancelar o cualquier tecla para continuar...
pause >nul

cd /d "%~dp0"

echo Ejecutando test...
echo.
backend\.venv\Scripts\python.exe test_propagacion_bracket.py

echo.
echo ============================================================
echo  Listo. Presiona cualquier tecla para cerrar.
echo ============================================================
pause >nul
