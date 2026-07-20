# fix_stats_excel_y_recalcular.ps1
# Aplica correcciones de partido (minuto_gol + var) desde Excel y recalcula puntajes

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "FIX STATS EXCEL + RECALCULAR PUNTAJES" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Ejecutar SQL
Write-Host "`n[1/3] Ejecutando fix_partido_stats_from_excel.sql..." -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\fix_partido_stats_from_excel.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al ejecutar SQL" -ForegroundColor Red
    pause; exit 1
}
Write-Host "OK - SQL ejecutado" -ForegroundColor Green

# 2. Login
Write-Host "`n[2/3] Obteniendo token..." -ForegroundColor Yellow
$loginBody = '{"username":"jose","password":"catalina"}'
$loginResp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
$token = $loginResp.access_token
if (-not $token) {
    Write-Host "ERROR: No se pudo obtener token. Verifica que uvicorn este activo." -ForegroundColor Red
    pause; exit 1
}
Write-Host "OK - Token obtenido" -ForegroundColor Green

# 3. Recalcular
Write-Host "`n[3/3] Recalculando puntajes (POST /calcular-puntajes/2)..." -ForegroundColor Yellow
$headers = @{ Authorization = "Bearer $token" }
$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/bets/calcular-puntajes/2" -Method POST -Headers $headers
Write-Host "Partidos procesados: $($result.partidos_procesados)" -ForegroundColor Green
Write-Host "Plenos (marcador exacto): $($result.plenos)" -ForegroundColor Green
Write-Host "Aciertos (resultado): $($result.aciertos)" -ForegroundColor Green

Write-Host "`n=============================================" -ForegroundColor Cyan
Write-Host "COMPLETADO OK. Verifica el ranking en el portal." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
pause
