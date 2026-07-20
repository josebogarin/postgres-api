@echo off
cd /d "C:\proyecto FAST API"
echo === COMPARAR RESULTADO (marcador + quien pasa) de TODOS los partidos: Excel vs BD ===
call backend\.venv\Scripts\python.exe comparar_resultados_todos.py
echo.
pause
