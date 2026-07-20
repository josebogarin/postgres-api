@echo off
curl -s http://localhost:4040/api/tunnels > "%~dp0ngrok_status.txt" 2>&1
echo URL guardada en ngrok_status.txt
type "%~dp0ngrok_status.txt"
pause
