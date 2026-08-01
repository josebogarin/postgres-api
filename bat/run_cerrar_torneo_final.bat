@echo off
cd /d "%~dp0.."
echo === CIERRE DEL TORNEO: correr DESPUES de la Final (P104) y 3er puesto (P103) ===
echo === Requiere uvicorn en :8000 ===
call backend\.venv\Scripts\python.exe cerrar_torneo_final.py
echo.
pause
