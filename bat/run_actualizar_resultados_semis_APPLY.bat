@echo off
cd /d "%~dp0.."
echo === APPLY: escribe items de SEMIFINAL en la BD desde el Excel ===
call backend\.venv\Scripts\python.exe actualizar_resultados_fase.py semis --apply
echo.
pause
