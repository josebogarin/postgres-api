@echo off
chcp 65001 >nul
echo ============================================================
echo  SYNC SOFASCORE DIRECTO (sin servidor uvicorn)
echo  J=Amarillas  K=Rojas  L=VAR  M=Penales partido
echo ============================================================
echo.
cd /D "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe sync_sofascore_directo.py ayer
echo.
pause
