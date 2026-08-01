@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === DRY-RUN (no escribe) ===
python poblar_octavos_sudamericana.py
echo.
set /p OK="Crear octavos con los sembrados? escribi SI y Enter: "
if /I "%OK%"=="SI" (
  python poblar_octavos_sudamericana.py --apply
)
pause
