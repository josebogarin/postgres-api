@echo off
cd /d "%~dp0.."
echo === RECALCULO FORZADO de TODO el torneo (arregla items STALE en grupos) ===
echo === Requiere uvicorn en :8000 ===
call backend\.venv\Scripts\python.exe recalc_force_grupos.py
echo.
pause
