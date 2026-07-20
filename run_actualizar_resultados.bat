@echo off
echo ========================================
echo  BECBUC - Actualizar resultados desde Excel
echo ========================================
echo.
cd /d "C:\proyecto FAST API"
backend\.venv\Scripts\python.exe actualizar_resultados_desde_excel.py
echo.
pause
