@echo off
cd /d "%~dp0.."
echo === COMPARAR items OFICIALES OCTAVOS (P089-P096): Excel vs BD ===
call backend\.venv\Scripts\python.exe comparar_items_resultados.py octavos
echo.
pause
