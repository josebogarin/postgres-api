@echo off
cd /d "%~dp0.."
echo === REABRIR + RECALCULAR (force_grupos) + RE-CERRAR torneo 2 ===
echo (uvicorn en :8000 debe estar activo. El calcular tarda 1-3 min, esperar)
call backend\.venv\Scripts\python.exe reabrir_y_recalcular.py
echo.
pause
