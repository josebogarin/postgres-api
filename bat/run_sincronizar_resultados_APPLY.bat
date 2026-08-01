@echo off
cd /d "%~dp0.."
echo === APPLY: alinea resultados oficiales de la BD al Excel (escribe en partido) ===
call backend\.venv\Scripts\python.exe sincronizar_resultados_excel.py --apply
echo.
pause
