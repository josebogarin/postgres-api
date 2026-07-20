@echo off
title Reiniciar uvicorn BECBUC
echo Deteniendo uvicorn anterior...
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq BECBUC-Server*" 2>nul
timeout /t 2 /nobreak >nul

echo Iniciando uvicorn...
cd /d "C:\proyecto FAST API\backend"
start "BECBUC-Server" cmd /k ".venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
echo.
echo Servidor reiniciado. Espera 5 segundos y recarga la pagina.
timeout /t 5
