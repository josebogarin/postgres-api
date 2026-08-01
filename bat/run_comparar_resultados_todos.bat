@echo off
cd /d "%~dp0.."
echo === COMPARAR RESULTADO (marcador + quien pasa) de TODOS los partidos: Excel vs BD ===
call backend\.venv\Scripts\python.exe comparar_resultados_todos.py
echo.
pause
