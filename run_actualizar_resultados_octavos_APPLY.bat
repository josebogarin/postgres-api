@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: escribe items de OCTAVOS (P089-P096) en la BD desde el Excel ===
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py octavos --apply
echo.
pause
