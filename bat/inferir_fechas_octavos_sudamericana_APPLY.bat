@echo off
echo ============================================
echo   Sudamericana - inferir fechas de OCTAVOS (APLICAR)
echo ============================================
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python inferir_fechas_octavos_sudamericana.py --apply
echo.
pause
