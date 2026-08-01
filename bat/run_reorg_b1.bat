@echo off
chcp 65001 >nul
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\reorg_fase_b1.ps1"
