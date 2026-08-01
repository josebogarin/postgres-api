@echo off
echo =========================================
echo  Importar fechas/horas KO FIFA 2026
echo =========================================
cd /d "%~dp0..\backend"
.venv\Scripts\python.exe ..\importar_fechas_ko.py
echo.
pause
