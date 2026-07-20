@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\proyecto FAST API\reorg_fase_b1.ps1"
echo ---- launcher fin ----
