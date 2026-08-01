@echo off
echo ============================================
echo   Sudamericana OCTAVOS - fechas/horas desde ESPN
echo ============================================
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python inferir_fechas_espn.py %1
echo.
pause
