@echo off
chcp 65001 >nul
echo === Sembrando Copa Sudamericana en competicion (becbuc) ===
powershell -NoProfile -Command "Get-Content -Raw -Encoding UTF8 'C:\proyecto FAST API\documentacion\migraciones\seed_copa_sudamericana.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo === Competiciones actuales ===
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT id, nombre, tipo, api_league_id FROM competicion ORDER BY id;"
pause
