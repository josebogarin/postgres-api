Write-Host "RESET KO - Elimina resultados simulados de fases KO" -ForegroundColor Yellow
Write-Host "Conserva: equipos R32, apuestas de apostadores, puntajes grupos" -ForegroundColor Cyan
Write-Host ""
Write-Host "ATENCION: Esto borra todos los resultados de partidos KO." -ForegroundColor Red
$confirm = Read-Host "Escribi SI para confirmar"
if ($confirm -ne "SI") { Write-Host "Cancelado."; exit }

Write-Host "Ejecutando reset..." -ForegroundColor Cyan
Get-Content "C:\proyecto FAST API\documentacion\reset_ko_resultados.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

Write-Host "Reset completado." -ForegroundColor Green
Write-Host "Correr POST /calcular-puntajes desde el portal para verificar." -ForegroundColor Cyan
