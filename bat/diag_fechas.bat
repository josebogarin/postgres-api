@echo off
cd /d "%~dp0.."
echo Diagnosticando fechas en BD...
backend\.venv\Scripts\python.exe diag_fechas.py > diag_fechas_output.txt 2>&1
echo.
echo Resultado guardado en diag_fechas_output.txt
type diag_fechas_output.txt
pause
