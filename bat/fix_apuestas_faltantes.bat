@echo off
echo ============================================================
echo  FIX: Insertar apuestas faltantes y recalcular puntajes
echo ============================================================
echo.
cd /d "%~dp0.."
backend\.venv\Scripts\python.exe sync_paux_faltantes.py
echo.
pause
