@echo off
echo ============================================
echo BECBUC - Fix pts_penales_partido + Recalcular
echo ============================================
echo.

echo [1/2] Ejecutando migracion fix_pts_penales_partido.sql...
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\fix_pts_penales_partido.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.

echo [2/2] Recalculando puntajes via API...
cd /d "C:\proyecto FAST API"
"C:\proyecto FAST API\backend\.venv\Scripts\python.exe" recalcular_puntajes.py
echo.

echo Listo. Recarga becbuc-live.html en el navegador.
pause
