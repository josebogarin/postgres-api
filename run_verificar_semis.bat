@echo off
cd /d "C:\proyecto FAST API"
echo === VERIFICAR apuestas SEMIFINAL: Excel vs BD (solo lectura) ===
call backend\.venv\Scripts\python.exe verificar_semis_excel_vs_bd.py
echo.
pause
