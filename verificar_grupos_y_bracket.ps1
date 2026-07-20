# verificar_grupos_y_bracket.ps1
# Verifica el estado actual de los grupos y ejecuta avanzar-bracket si estan completos
# Doble-click para correr

$BASE  = "http://localhost:8000"
$TORNEO_ID = 2

Write-Host "=== BECBUC: Verificacion de Grupos y Bracket ===" -ForegroundColor Cyan
Write-Host "$(Get-Date -Format 'HH:mm:ss')`n" -ForegroundColor Gray

# 1. Login
try {
    $loginResp = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/auth/login" `
        -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}'
    $TOKEN = $loginResp.access_token
    if (-not $TOKEN) { throw "No token" }
    Write-Host "Login OK" -ForegroundColor Green
} catch {
    Write-Host "ERROR login: $_" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

$headers = @{ "Authorization" = "Bearer $TOKEN" }

# 2. Ver estado de grupos
Write-Host "`n--- GRUPOS ---" -ForegroundColor Yellow
try {
    $grupos = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/grupos/$TORNEO_ID" -Headers $headers
    $fases = $grupos.fases
    $totalFin = 0
    $totalPend = 0
    $gruposCompletos = 0
    $gruposIncompletos = 0

    foreach ($fase in $fases) {
        $partidos = $fase.partidos
        $fin  = ($partidos | Where-Object { $_.estado -eq 'finalizado' }).Count
        $pend = ($partidos | Where-Object { $_.estado -ne 'finalizado' }).Count
        $totalFin  += $fin
        $totalPend += $pend
        $color = if ($pend -eq 0) { "Green" } else { "Yellow" }
        $mark  = if ($pend -eq 0) { "✓" } else { "⏳ falta $pend" }
        Write-Host ("  {0,-25} {1,2}/{2} partidos fin  {3}" -f $fase.nombre, $fin, $partidos.Count, $mark) -ForegroundColor $color
        if ($pend -eq 0) { $gruposCompletos++ } else { $gruposIncompletos++ }
    }

    Write-Host "`n  Total partidos finalizados : $totalFin" -ForegroundColor White
    Write-Host "  Grupos completos           : $gruposCompletos" -ForegroundColor White
    Write-Host "  Grupos incompletos         : $gruposIncompletos" -ForegroundColor $(if ($gruposIncompletos -eq 0) { "Green" } else { "Yellow" })
} catch {
    Write-Host "ERROR al leer grupos: $_" -ForegroundColor Red
}

# 3. Ver estado actual del bracket R32
Write-Host "`n--- BRACKET R32 ---" -ForegroundColor Yellow
try {
    $br = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TORNEO_ID" -Headers $headers
    $r32 = $br.partidos | Where-Object { $_.tipo -eq 'ronda32' -or $_.fase -like '*16avos*' -or $_.fase -like '*ronda32*' }
    if (-not $r32) { $r32 = $br.partidos | Select-Object -First 16 }

    $conEquipo = ($r32 | Where-Object { $null -ne $_.local }).Count
    $sinEquipo = ($r32 | Where-Object { $null -eq $_.local }).Count

    Write-Host ("  Partidos R32: {0} | Con equipos: {1} | Sin equipos: {2}" -f $r32.Count, $conEquipo, $sinEquipo) `
        -ForegroundColor $(if ($sinEquipo -eq 0) { "Green" } elseif ($conEquipo -gt 0) { "Yellow" } else { "Red" })

    if ($r32.Count -gt 0) {
        foreach ($p in $r32 | Select-Object -First 8) {
            $loc = if ($p.local) { $p.local.nombre } else { "Por definir" }
            $vis = if ($p.visitante) { $p.visitante.nombre } else { "Por definir" }
            $col = if ($p.local -and $p.visitante) { "Cyan" } else { "DarkGray" }
            Write-Host ("    P{0,-3} {1,-22} vs {2}" -f $p.num, $loc, $vis) -ForegroundColor $col
        }
    }
} catch {
    Write-Host "ERROR al leer bracket: $_" -ForegroundColor Red
}

# 4. Preguntar si avanzar bracket
Write-Host ""
if ($gruposIncompletos -eq 0) {
    Write-Host "Todos los grupos estan completos!" -ForegroundColor Green
    $resp = Read-Host "Avanzar bracket y sincronizar ahora? (s/n)"
    if ($resp -eq 's' -or $resp -eq 'S') {
        Write-Host "`nAvanzando bracket..." -ForegroundColor Yellow
        try {
            $r = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/avanzar-bracket/$TORNEO_ID" -Headers $headers
            Write-Host "  OK" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR: $_" -ForegroundColor Red
        }

        Write-Host "Sincronizando desde API-Football..." -ForegroundColor Yellow
        try {
            $s = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/sync-resultados/$TORNEO_ID?force=true" -Headers $headers
            Write-Host "  OK - $($s.actualizados) actualizado(s)" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR sync: $_" -ForegroundColor Yellow
        }

        Write-Host "Recalculando puntajes..." -ForegroundColor Yellow
        try {
            $pts = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/calcular-puntajes/$TORNEO_ID" -Headers $headers
            Write-Host "  OK" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR puntajes: $_" -ForegroundColor Yellow
        }

        # Mostrar bracket actualizado
        Write-Host "`n--- BRACKET R32 ACTUALIZADO ---" -ForegroundColor Cyan
        try {
            $br2 = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TORNEO_ID" -Headers $headers
            $r32b = $br2.partidos | Where-Object { $_.tipo -eq 'ronda32' }
            if (-not $r32b) { $r32b = $br2.partidos | Select-Object -First 16 }
            foreach ($p in $r32b) {
                $loc = if ($p.local) { $p.local.nombre } else { "Por definir" }
                $vis = if ($p.visitante) { $p.visitante.nombre } else { "Por definir" }
                $col = if ($p.local -and $p.visitante) { "Green" } else { "Red" }
                Write-Host ("  P{0,-3} {1,-22} vs {2}" -f $p.num, $loc, $vis) -ForegroundColor $col
            }
        } catch {}
    }
} else {
    Write-Host "Hay $gruposIncompletos grupo(s) incompleto(s). Esperando a que terminen..." -ForegroundColor Yellow
    Write-Host "Cuando terminen los ultimos partidos, corre este script de nuevo." -ForegroundColor White
}

Write-Host "`n=== FIN ===" -ForegroundColor Cyan
Read-Host "`nPresiona Enter para cerrar"
