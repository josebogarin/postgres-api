@echo off
taskkill /f /im cloudflared.exe 2>nul
taskkill /f /im ngrok.exe 2>nul
timeout /t 2 /nobreak >nul
echo Iniciando Cloudflare Tunnel... > "C:\proyecto FAST API\cloudflared.log"
"C:\proyecto FAST API\cloudflared.exe" tunnel --url http://localhost:8000 >> "C:\proyecto FAST API\cloudflared.log" 2>&1
