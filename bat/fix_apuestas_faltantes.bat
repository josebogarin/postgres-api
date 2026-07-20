@echo off
echo ============================================================
echo  FIX: Insertar apuestas faltantes y recalcular puntajes
echo ============================================================
echo.
cd /d "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe sync_paux_faltantes.py
echo.
pause
