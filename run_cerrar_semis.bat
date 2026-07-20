@echo off
cd /d "C:\proyecto FAST API"
echo === CERRAR SEMIFINAL: calcular puntajes + bloquear fase semis ===
echo (requiere uvicorn en :8000 y Docker core-postgres)
call backend\.venv\Scripts\python.exe cerrar_semis.py
echo.
pause
