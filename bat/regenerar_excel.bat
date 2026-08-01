@echo off
echo Asegurate que uvicorn este corriendo en el puerto 8000 antes de continuar.
echo.
pause
powershell -ExecutionPolicy Bypass -WindowStyle Normal -File "%~dp0..\regenerar_excel.ps1"
pause
