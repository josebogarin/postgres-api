@echo off
cd /d "%~dp0.."
echo === DRY RUN: actualizar items de SEMIFINAL en BD desde Excel (no escribe) ===
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py semis
echo.
pause
