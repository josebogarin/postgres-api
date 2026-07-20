Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FIX VAR DISCREPANCIAS - Datos del Excel oficial" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Actualizando P025, P064, P070, P071..." -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\fix_var_discrepancias.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
Write-Host ""
Write-Host "Listo. Ahora recalcular puntajes para que J/L/M/N se actualicen." -ForegroundColor Green
Write-Host "Ejecutar desde el portal: Herramientas -> Calcular puntajes" -ForegroundColor Green
Write-Host ""
pause
