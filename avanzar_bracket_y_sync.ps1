# avanzar_bracket_y_sync.ps1
# Llama al API para avanzar bracket (poblar equipos R32 desde standings de grupos)
# y luego sincroniza puntajes.
# Ejecutar con: click derecho -> Ejecutar con PowerShell
# O desde terminal: .\avanzar_bracket_y_sync.ps1

$BASE  = "http://localhost:8000"
$TORNEO_ID = 2

Write-Host "=== BECBUC: Avanzar Bracket + Sync ===" -ForegroundColor Cyan

# 1. Login
Write-Host "`n1. Iniciando sesion como jose..." -ForegroundColor Yellow
try {
    $loginBody = '{"username":"jose","password":"catalina"}'
    $loginResp = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/auth/login" `
        -ContentType "application/json" -Body $loginBody
    $TOKEN = $loginResp.access_token
    if (-not $TOKEN) { throw "No se obtuvo token" }
    Write-Host "   OK - Token obtenido" -ForegroundColor Green
} catch {
    Write-Host "   ERROR login: $_" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

$headers = @{ "Authorization" = "Bearer $TOKEN" }

# 2. Avanzar bracket
Write-Host "`n2. Avanzando bracket (poblando equipos R32 desde standings)..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/avanzar-bracket/$TORNEO_ID" -Headers $headers
    Write-Host "   OK - Bracket avanzado" -ForegroundColor Green
    if ($r.mensaje) { Write-Host "   $($r.mensaje)" }
} catch {
    Write-Host "   ERROR avanzar bracket: $_" -ForegroundColor Red
}

# 3. Sincronizar resultados desde API-Football
Write-Host "`n3. Sincronizando resultados desde API-Football..." -ForegroundColor Yellow
try {
    $s = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/sync-resultados/$TORNEO_ID?force=true" -Headers $headers
    $act = $s.actualizados ?? 0
    Write-Host "   OK - $act partido(s) actualizado(s)" -ForegroundColor Green
    if ($s.puntajes_ok) {
        $pl = $s.puntajes?.plenos ?? 0
        Write-Host "   Puntajes calculados - $pl plenos" -ForegroundColor Green
    }
} catch {
    Write-Host "   ERROR sync: $_ (puede ser normal si no hay partidos activos)" -ForegroundColor Yellow
}

# 4. Recalcular puntajes explicitamente
Write-Host "`n4. Recalculando puntajes..." -ForegroundColor Yellow
try {
    $pts = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/calcular-puntajes/$TORNEO_ID" -Headers $headers
    $pl = $pts.plenos ?? $pts.partidos_procesados ?? "OK"
    Write-Host "   OK - Puntajes actualizados ($pl plenos)" -ForegroundColor Green
} catch {
    Write-Host "   ERROR calcular puntajes: $_" -ForegroundColor Yellow
}

# 5. Verificar bracket actual
Write-Host "`n5. Verificando bracket R32..." -ForegroundColor Yellow
try {
    $br = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TORNEO_ID" -Headers $headers
    $r32 = $br.partidos | Where-Object { $_.tipo -eq 'ronda32' }
    $conEquipo = ($r32 | Where-Object { $_.local -ne $null }).Count
    $sinEquipo = ($r32 | Where-Object { $_.local -eq $null }).Count
    Write-Host "   R32: $($r32.Count) partidos | Con equipos: $conEquipo | Sin equipos: $sinEquipo" -ForegroundColor $(if ($sinEquipo -eq 0) { "Green" } else { "Yellow" })
    if ($r32.Count -gt 0) {
        Write-Host "`n   Primeros 4 partidos R32:" -ForegroundColor White
        $r32 | Select-Object -First 4 | ForEach-Object {
            $loc = if ($_.local) { $_.local.nombre } else { "Por definir" }
            $vis = if ($_.visitante) { $_.visitante.nombre } else { "Por definir" }
            Write-Host "     P$($_.num): $loc vs $vis" -ForegroundColor $(if ($_.local -and $_.visitante) { "Cyan" } else { "DarkGray" })
        }
    }
} catch {
    Write-Host "   ERROR verificar bracket: $_" -ForegroundColor Red
}

Write-Host "`n=== LISTO ===" -ForegroundColor Cyan
Write-Host "Ahora refrescar becbuc-live.html en el celular (o agregar ?v=2 a la URL)" -ForegroundColor White
Write-Host "Los equipos del bracket deben aparecer al ir a la pestana Bracket" -ForegroundColor White
Read-Host "`nPresiona Enter para cerrar"
