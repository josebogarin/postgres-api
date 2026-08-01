@echo off
echo ============================================
echo   BECBUC - Control de fechas por fase (Live)
echo ============================================
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python verificar_fechas_fases.py %1
echo.
pause
