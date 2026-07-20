@echo off
chcp 65001 >nul
echo ============================================================
echo  SYNC PARTIDOS DE AYER + RECALCULO PUNTAJES
echo ============================================================
echo.
cd /D "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe sync_ayer.py
echo.
pause
