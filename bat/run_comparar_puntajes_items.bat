@echo off
cd /d "%~dp0.."
echo === COMPARAR PUNTAJES por apostador x partido, item por item: Excel vs BD ===
echo (todas las fases hasta semis)
call backend\.venv\Scripts\python.exe comparar_puntajes_items.py todas
echo.
pause
