@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: bloquear Final + 3er puesto (cierra el editor de apuestas) ===
call backend\.venv\Scripts\python.exe bloquear_final_3p.py --apply
echo.
pause
