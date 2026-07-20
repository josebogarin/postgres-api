@echo off
cd /d "C:\proyecto FAST API"
start "BECBUC-Ngrok" cmd /k "ngrok.exe http 8000"
