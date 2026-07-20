@echo off
Get-Content no 2>nul
docker exec -i core-postgres psql -U app_user -d becbuc < "C:\proyecto FAST API\query_tarjetas.sql" > "C:\proyecto FAST API\resultado_tarjetas.txt" 2>&1
echo.
echo === RESULTADO ===
type "C:\proyecto FAST API\resultado_tarjetas.txt"
echo.
pause
