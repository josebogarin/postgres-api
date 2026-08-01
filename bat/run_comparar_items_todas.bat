@echo off
cd /d "%~dp0.."
echo === COMPARAR items OFICIALES TODAS LAS FASES (grupos..semis): Excel vs BD ===
call backend\.venv\Scripts\python.exe comparar_items_resultados.py todas
echo.
pause
