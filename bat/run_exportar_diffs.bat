@echo off
cd /d "%~dp0.."
echo === Exportar Excel con los diffs de puntajes etiquetados por causa ===
call backend\.venv\Scripts\python.exe exportar_diffs_puntajes.py
echo.
pause
