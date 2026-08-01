@echo off
echo === Sudamericana OCTAVOS - fechas/horas desde ESPN ===
cd /d "%~dp0.."
call backend\.venv\Scripts\activate.bat
python inferir_fechas_espn.py sudamericana %1
echo.
pause
