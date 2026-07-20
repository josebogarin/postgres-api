# run_migrate_and_populate.ps1
# Ejecutar: click derecho -> "Run with PowerShell" o desde terminal

Write-Host "=== Paso 1: Ejecutar migracion v4 (minuto por fuente) ===" -ForegroundColor Cyan
Get-Content "C:\proyecto FAST API\documentacion\migracion_stats_fuentes.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
Write-Host "Migracion OK" -ForegroundColor Green

Write-Host ""
Write-Host "=== Paso 2: Login para obtener token ===" -ForegroundColor Cyan
$loginBody = '{"username":"jose","password":"catalina"}'
$loginResp = irm "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
$tok = $loginResp.access_token
Write-Host "Token obtenido: $($tok.Substring(0,20))..." -ForegroundColor Green

Write-Host ""
Write-Host "=== Paso 3: Populate stats fuentes (todos los partidos) ===" -ForegroundColor Cyan
$result = irm "http://localhost:8000/api/v1/bets/populate-stats-fuentes/2" -Method POST -Headers @{Authorization="Bearer $tok"}
Write-Host "Resultado:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 3

Write-Host ""
Write-Host "=== Paso 4: Verificar Colombia vs Congo ===" -ForegroundColor Cyan
$check = irm "http://localhost:8000/api/v1/bets/stats-fuentes/2?estado=finalizado" -Method GET -Headers @{Authorization="Bearer $tok"}
$colombia = $check.partidos | Where-Object { $_.local -like "*Colombia*" -or $_.visitante -like "*Colombia*" }
$colombia | ConvertTo-Json -Depth 2

Read-Host "Presiona Enter para cerrar"
