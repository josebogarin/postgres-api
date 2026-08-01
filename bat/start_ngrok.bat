@echo off
cd /d "%~dp0.."
start "BECBUC-Ngrok" cmd /k "ngrok.exe http 8000"
