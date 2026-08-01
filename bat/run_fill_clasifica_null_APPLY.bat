@echo off
cd /d "%~dp0.."
echo === APPLY: rellenar pred_equipo_clasifica NULL en KO desde Excel corregido (ESCRIBE en BD) ===
call backend\.venv\Scripts\python.exe fill_clasifica_null.py --apply
echo.
pause
