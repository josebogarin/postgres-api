@echo off
chcp 65001 >nul
echo ============================================
echo  POBLAR equipo.codigo_iso + fifa_ranking
echo ============================================
echo.
cd /d "C:\proyecto FAST API"

echo [1/2] DRY-RUN -- mostrando lo que se actualizaria...
echo.
backend\.venv\Scripts\python.exe poblar_equipos_iso_ranking.py
echo.
echo ============================================
set /p CONFIRM="Aplicar cambios? (s/N): "
if /i "%CONFIRM%"=="s" (
    echo.
    echo [2/2] Aplicando cambios...
    backend\.venv\Scripts\python.exe poblar_equipos_iso_ranking.py --apply
    echo.
) else (
    echo Cancelado.
)
echo.
pause
