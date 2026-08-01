@echo off
taskkill /f /im cloudflared.exe 2>nul
taskkill /f /im ngrok.exe 2>nul
timeout /t 2 /nobreak >nul
echo Iniciando Cloudflare Tunnel... > "%~dp0..\cloudflared.log"
"%~dp0..\cloudflared.exe" tunnel --url http://localhost:8000 >> "%~dp0..\cloudflared.log" 2>&1
