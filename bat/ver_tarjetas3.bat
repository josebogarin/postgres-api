@echo off
Get-Content no 2>nul
docker exec -i core-postgres psql -U app_user -d becbuc < "%~dp0..\query_tarjetas.sql" > "%~dp0..\resultado_tarjetas.txt" 2>&1
echo.
echo === RESULTADO ===
type "%~dp0..\resultado_tarjetas.txt"
echo.
pause
