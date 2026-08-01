@echo off
cd /d "%~dp0.."
echo === RECALCULAR puntajes de TODO el torneo hasta SEMIS ===
echo (desbloquea temporalmente, recalcula y restaura el bloqueo)
echo (requiere uvicorn en :8000 y Docker core-postgres)
call backend\.venv\Scripts\python.exe recalc_hasta_semis.py
echo.
pause
