# run_fix_pts_equipo_grupos.ps1
# Ejecutar como administrador si docker no responde

Write-Host "Aplicando fix: pts_equipo=0 para grupos (elimina doble conteo item P)..." -ForegroundColor Cyan

$sql = Get-Content "C:\proyecto FAST API\documentacion\fix_pts_equipo_grupos.sql" -Raw
$sql | docker exec -i core-postgres psql -U app_user -d becbuc

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Fix aplicado correctamente." -ForegroundColor Green
    Write-Host ""
    Write-Host "Ahora recalcular puntajes KO solamente (grupos bloqueados, no se tocan):" -ForegroundColor Yellow
    Write-Host "  POST /api/v1/bets/calcular-puntajes/2  desde el portal" -ForegroundColor Yellow
} else {
    Write-Host "❌ Error al ejecutar SQL. Verificar que Docker está corriendo." -ForegroundColor Red
}

Read-Host "Presioná Enter para salir"
