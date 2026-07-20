@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: re-importar predicciones de bonus (TBL MASTER -^> apuesta) - no escribe ===
call backend\.venv\Scripts\python.exe reimportar_predicciones_bonus.py
echo.
pause
