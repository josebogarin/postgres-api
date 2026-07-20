@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: escribe predicciones de bonus desde TBL MASTER en la BD ===
echo Luego correr run_recalc_hasta_semis.bat para re-puntuar.
call backend\.venv\Scripts\python.exe reimportar_predicciones_bonus.py --apply
echo.
pause
