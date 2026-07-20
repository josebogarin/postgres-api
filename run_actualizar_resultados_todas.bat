@echo off
cd /d "C:\proyecto FAST API"
echo === DRY RUN: actualizar items oficiales de TODAS las fases (grupos..semis) - no escribe ===
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py todas
echo.
pause
