@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === DRY-RUN: revisa que cada equipo matchee el club del pais correcto ===
python buscar_logos_equipos.py
echo.
set /p OK="Los matches son correctos? escribi SI y Enter para guardar los logos: "
if /I "%OK%"=="SI" python buscar_logos_equipos.py --apply
pause
