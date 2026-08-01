@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === DRY-RUN (no escribe) ===
python cargar_fixture_libertadores_octavos.py
echo.
set /p OK="Escribir en la BD? escribi SI y Enter: "
if /I "%OK%"=="SI" (
  python cargar_fixture_libertadores_octavos.py --apply
)
pause
