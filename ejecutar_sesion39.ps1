# BECBUC Sesion 39 - Migracion stats_fuentes + backfill
# Ejecutar como: cd "C:\proyecto FAST API" && .\ejecutar_sesion39.ps1

Write-Host "=== BECBUC Sesion 39 ===" -ForegroundColor Cyan

# 1. Migracion SQL
Write-Host "`n[1/3] Ejecutando migracion SQL..." -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\migracion_stats_fuentes.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
if ($LASTEXITCODE -ne 0) { Write-Host "AVISO: posible error en SQL (puede ser normal si la tabla ya existe)" -ForegroundColor DarkYellow }

# 2. Verificar tabla
Write-Host "`n[2/3] Verificando tabla partido_stats_fuentes..." -ForegroundColor Yellow
docker exec core-postgres psql -U app_user -d becbuc -c "\d partido_stats_fuentes"

# 3. Login y backfill
Write-Host "`n[3/3] Backfill via API..." -ForegroundColor Yellow
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST `
    -ContentType "application/json" `
    -Body '{"username":"jose","password":"catalina"}'
$token = $login.access_token
Write-Host "  Login OK, token obtenido" -ForegroundColor Green

$headers = @{ Authorization = "Bearer $token" }
$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/bets/populate-stats-fuentes/2" `
    -Method POST -Headers $headers
Write-Host "  Resultado:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 3

Write-Host "`nListo!" -ForegroundColor Green
