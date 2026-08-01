@echo off
chcp 65001 >nul
cd /d "%~dp0."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reorg_fase_b1.ps1"
echo ---- launcher fin ----
