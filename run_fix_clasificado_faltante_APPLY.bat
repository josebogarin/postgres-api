@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: setear equipo_clasificado_id inferido en los KO que faltan ===
echo Luego correr run_recalc_hasta_semis.bat
call backend\.venv\Scripts\python.exe fix_clasificado_faltante.py --apply
echo.
pause
