@echo off
cd /d "%~dp0.."
echo === COMPARAR items OFICIALES P101/P102: Excel vs BD (solo lectura) ===
call backend\.venv\Scripts\python.exe comparar_items_semis.py
echo.
pause
