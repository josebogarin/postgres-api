@echo off
chcp 65001 >nul
cd /d "C:\proyecto FAST API"
echo === PROPAGAR (dry-run) Libertadores(1) + Sudamericana(14) ===
python propagar_ganadores_clubes.py 1
python propagar_ganadores_clubes.py 14
echo.
set /p OK="Aplicar propagacion en la BD? escribi SI: "
if /I "%OK%"=="SI" (
  python propagar_ganadores_clubes.py 1 --apply
  python propagar_ganadores_clubes.py 14 --apply
)
pause
