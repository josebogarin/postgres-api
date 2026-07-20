@echo off
echo Matando procesos ngrok existentes...
taskkill /f /im ngrok.exe 2>nul
timeout /t 2 /nobreak >nul
echo Arrancando ngrok...
start "BECBUC - ngrok" cmd /k "cd /d "C:\proyecto FAST API" && ngrok.exe http 8000"
echo Listo.
