@echo off
echo =============================================
echo BECBUC Sesion 39 - Migracion + Backfill
echo =============================================
echo.

echo [1/3] Ejecutando migracion SQL en Docker...
docker exec -i core-postgres psql -U app_user -d becbuc < "%~dp0..\documentacion\migracion_stats_fuentes.sql"
echo.

echo [2/3] Verificando tabla...
docker exec core-postgres psql -U app_user -d becbuc -c "\d partido_stats_fuentes"
echo.

echo [3/3] Haciendo login y backfill via API...
powershell -Command "$login = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -ContentType 'application/json' -Body '{\"username\":\"jose\",\"password\":\"catalina\"}'; $tok = $login.access_token; Write-Host 'Token OK'; $r = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/bets/populate-stats-fuentes/2' -Method POST -Headers @{Authorization=\"Bearer $tok\"}; $r | ConvertTo-Json -Depth 3"
echo.

echo =============================================
echo Listo! Ver resultados arriba.
echo =============================================
pause
