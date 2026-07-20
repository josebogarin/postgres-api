# BECBUC - Migración fair play + recálculo
# Ejecutar con: Right-click -> "Ejecutar con PowerShell"

$ErrorActionPreference = "Stop"
$base = "http://localhost:8000/api/v1"

Write-Host "=== BECBUC Fair Play Setup ===" -ForegroundColor Cyan

# 1. Migración SQL
Write-Host "`n[1/3] Ejecutando migración SQL en Docker..." -ForegroundColor Yellow
try {
    Get-Content "C:\proyecto FAST API\documentacion\migracion_fair_play_partido.sql" |
        docker exec -i core-postgres psql -U app_user -d becbuc
    Write-Host "  ✓ Migración OK" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Error en migración (puede ya estar aplicada): $_" -ForegroundColor Yellow
}

# 2. Login para obtener token
Write-Host "`n[2/3] Login como jose/catalina..." -ForegroundColor Yellow
$loginBody = '{"username":"jose","password":"catalina"}'
$loginResp = Invoke-RestMethod -Uri "$base/auth/login" -Method POST `
    -ContentType "application/json" -Body $loginBody
$token = $loginResp.access_token
if (-not $token) { Write-Host "  ✗ Login fallido" -ForegroundColor Red; exit 1 }
Write-Host "  ✓ Token obtenido" -ForegroundColor Green

$headers = @{ Authorization = "Bearer $token" }

# 3. Recalcular fair play (baja datos de API-Football por equipo)
Write-Host "`n[3/3] Recalculando fair play desde API-Football..." -ForegroundColor Yellow
Write-Host "  (Esto puede tardar 30-60s — descarga ~72 fixtures)" -ForegroundColor DarkGray
try {
    $fpResp = Invoke-RestMethod -Uri "$base/bets/recalc-fair-play/2?max_partidos=80" `
        -Method POST -Headers $headers
    Write-Host "  ✓ Partidos actualizados: $($fpResp.actualizados)/$($fpResp.partidos_procesados)" -ForegroundColor Green
    Write-Host "  ✓ API calls usadas: $($fpResp.api_calls)" -ForegroundColor Green
    Write-Host "  ✓ Fair play recalculado: $($fpResp.fair_play_recalculado)" -ForegroundColor Green
    if ($fpResp.errores.Count -gt 0) {
        Write-Host "  ⚠ Errores: $($fpResp.errores | ConvertTo-Json -Compress)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Error: $_" -ForegroundColor Red
    exit 1
}

# 4. Recalcular puntajes
Write-Host "`n[4/4] Recalculando puntajes..." -ForegroundColor Yellow
try {
    $ptsResp = Invoke-RestMethod -Uri "$base/bets/calcular-puntajes/2" `
        -Method POST -Headers $headers
    Write-Host "  ✓ Puntajes OK: $($ptsResp.procesados) apostadores procesados" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Error en puntajes: $_" -ForegroundColor Yellow
}

Write-Host "`n=== LISTO ===" -ForegroundColor Cyan
Write-Host "El criterio FIFA de fair play está ahora activo en la selección de mejores terceros." -ForegroundColor White
Read-Host "`nPresioná Enter para cerrar"
