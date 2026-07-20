@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: escribe items oficiales de TODAS las fases (grupos..semis) en la BD ===
echo Luego correr run_recalc_hasta_semis.bat para re-puntuar.
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py todas --apply
echo.
pause
