Write-Host "=== Ejecutando migracion pronosticos_aux ===" -ForegroundColor Cyan
Get-Content "C:\proyecto FAST API\documentacion\migracion_pronosticos_aux.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
Write-Host ""
Write-Host "=== Verificacion ===" -ForegroundColor Green
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) as total, COUNT(DISTINCT nombre) as apostadores, MIN(id_partido) as desde, MAX(id_partido) as hasta FROM pronosticos_aux;"
Read-Host "Presiona Enter para cerrar"
