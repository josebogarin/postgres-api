@echo off
echo ============================================================
echo  BECBUC - Recalculo Fair Play + Sync Grupos
echo ============================================================
echo.
echo Paso 1: Sync historico (Paraguay + todos los grupos)
echo Paso 2: Recalc tarjetas por equipo (fair play)
echo Paso 3: Ranking mejores 8 terceros con FP
echo Paso 4: Recalcular puntajes apostadores
echo.
cd /d "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe recalc_fairplay.py
echo.
echo ============================================================
echo  Proceso finalizado. Podes cerrar esta ventana.
echo ============================================================
pause
