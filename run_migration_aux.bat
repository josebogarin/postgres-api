@echo off
powershell -Command "Get-Content 'C:\proyecto FAST API\documentacion\migracion_pronosticos_aux.sql' | docker exec -i core-postgres psql -U app_user -d becbuc"
echo.
echo === Verificacion ===
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) as total, COUNT(DISTINCT nombre) as apostadores, MIN(id_partido) AS desde, MAX(id_partido) AS hasta FROM pronosticos_aux;"
pause
