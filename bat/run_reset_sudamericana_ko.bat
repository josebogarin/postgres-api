@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python reset_sudamericana_ko.py
echo.
set /p OK="Limpiar KO de Sudamericana? escribi SI y Enter: "
if /I "%OK%"=="SI" python reset_sudamericana_ko.py --apply
pause
