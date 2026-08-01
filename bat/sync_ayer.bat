@echo off
chcp 65001 >nul
echo ============================================================
echo  SYNC PARTIDOS DE AYER + RECALCULO PUNTAJES
echo ============================================================
echo.
cd /D "%~dp0.."
backend\.venv\Scripts\python.exe sync_ayer.py
echo.
pause
