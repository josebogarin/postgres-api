@echo off
cd /d "C:\proyecto FAST API"
echo === Exporta a Excel las diferencias de puntaje (Excel de cierre vs BD) ===
call backend\.venv\Scripts\python.exe exportar_diffs_fin_torneo.py
echo.
pause
