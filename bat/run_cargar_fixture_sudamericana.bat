@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === DRY-RUN (no escribe) — revisa que cada llave matchee el partido correcto ===
python cargar_fixture_sudamericana_16avos.py
echo.
set /p OK="Los matches son correctos? escribi SI y Enter para guardar: "
if /I "%OK%"=="SI" (
  python cargar_fixture_sudamericana_16avos.py --apply
)
pause
