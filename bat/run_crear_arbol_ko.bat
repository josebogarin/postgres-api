@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === LIBERTADORES (torneo 1) - DRY RUN ===
python crear_arbol_ko_clubes.py 1
echo.
echo === SUDAMERICANA (torneo 14) - DRY RUN ===
python crear_arbol_ko_clubes.py 14
echo.
set /p OK="Crear Cuartos/Semis/Final en AMBOS torneos? escribi SI: "
if /I "%OK%"=="SI" (
  python crear_arbol_ko_clubes.py 1 --apply
  python crear_arbol_ko_clubes.py 14 --apply
)
pause
