@echo off
title Reiniciar ngrok
echo Cerrando ngrok anterior...
taskkill /f /im ngrok.exe 2>nul
timeout /t 2 /nobreak >nul
echo Iniciando ngrok en puerto 8000...
cd /d "%~dp0.."
start "" ngrok.exe http 8000
timeout /t 3 /nobreak >nul
echo.
echo ngrok iniciado. URL en: http://127.0.0.1:4040
echo (abriendo monitor...)
start http://127.0.0.1:4040
