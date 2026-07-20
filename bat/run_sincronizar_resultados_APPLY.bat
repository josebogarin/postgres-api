@echo off
cd /d "C:\proyecto FAST API"
echo === APPLY: alinea resultados oficiales de la BD al Excel (escribe en partido) ===
call backend\.venv\Scripts\python.exe sincronizar_resultados_excel.py --apply
echo.
pause
