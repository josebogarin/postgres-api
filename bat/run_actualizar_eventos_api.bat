@echo off
cd /d "C:\proyecto FAST API"
echo === Refresca eventos_api desde API-Football (solo el timeline, NO toca totales) ===
echo Uso: pasa 104 (final) o all (todos los KO). Default 104.
call backend\.venv\Scripts\python.exe actualizar_eventos_api.py %1
echo.
pause
