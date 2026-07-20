Set-Location "C:\proyecto FAST API\backend"

Write-Host "=== Eliminando git lock si existe ===" -ForegroundColor Yellow
Remove-Item ".git\index.lock" -Force -ErrorAction SilentlyContinue

Write-Host "=== Git commit y push ===" -ForegroundColor Yellow
git add -A
git commit -m "sesion 33+34: live panel ranking fix + totales por item"
git push

Write-Host "=== Migracion monitor.sql ===" -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\migracion_monitor.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

Write-Host "=== Fix partido_id apuestas v2 ===" -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\fix_partido_id_apuestas_v2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

Write-Host "=== LISTO ===" -ForegroundColor Green
Read-Host "Presiona Enter para cerrar"
