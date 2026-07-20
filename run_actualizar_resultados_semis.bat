@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: actualizar items de SEMIFINAL en BD desde Excel (no escribe) ===
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py semis
echo.
pause
