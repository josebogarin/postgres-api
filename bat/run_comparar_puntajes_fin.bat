@echo off
cd /d "C:\proyecto FAST API"
echo === AUDITORIA ORIGEN: puntos Excel fin de torneo vs BD (solo lectura) ===
call backend\.venv\Scripts\python.exe comparar_puntajes_fin_torneo.py
echo.
pause
