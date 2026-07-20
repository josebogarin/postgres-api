# run_todo.ps1 - Ejecuta todo sin pausas (compatible PowerShell 5)
$BASE = "http://localhost:8000"
$TID  = 2

function Step($msg) { Write-Host "" ; Write-Host $msg -ForegroundColor Cyan }
function OK($msg)   { Write-Host "  OK: $msg" -ForegroundColor Green }
function ERR($msg)  { Write-Host "  ERR: $msg" -ForegroundColor Red }
function NV($val, $def) { if ($null -ne $val) { $val } else { $def } }

Write-Host "=== BECBUC RUN TODO $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Magenta

# 1. Login
Step "1. Login"
try {
    $t = (Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/auth/login" `
        -ContentType "application/json" `
        -Body '{"username":"jose","password":"catalina"}').access_token
    OK "Token obtenido"
} catch { ERR $_; exit 1 }

$h = @{ "Authorization" = "Bearer $t" }

# 2. Estado de grupos
Step "2. Estado de grupos"
try {
    $g = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/grupos/$TID" -Headers $h
    $totalT = 0; $totalF = 0
    foreach ($f in $g.fases) {
        $fn = ($f.partidos | Where-Object { $_.estado -eq 'finalizado' }).Count
        $tp = $f.partidos.Count
        $totalT += $tp; $totalF += $fn
        if ($fn -eq $tp) {
            Write-Host ("    {0,-30} {1}/{2} OK" -f $f.nombre, $fn, $tp) -ForegroundColor Green
        } else {
            Write-Host ("    {0,-30} {1}/{2} pendiente" -f $f.nombre, $fn, $tp) -ForegroundColor Yellow
        }
    }
    Write-Host "  Total: $totalF / $totalT partidos finalizados" -ForegroundColor White
} catch { ERR $_ }

# 3. Sync desde API-Football
Step "3. Sync API-Football"
try {
    $s = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/sync-resultados/$TID?force=true" -Headers $h
    $act = NV $s.actualizados 0
    OK "$act partido(s) actualizado(s)"
} catch { Write-Host "  WARN sync: $_" -ForegroundColor Yellow }

# 4. Avanzar bracket
Step "4. Avanzar bracket"
try {
    $r = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/avanzar-bracket/$TID" -Headers $h
    OK "Bracket avanzado"
} catch { ERR $_ }

# 5. Calcular puntajes
Step "5. Calcular puntajes"
try {
    $pts = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/calcular-puntajes/$TID" -Headers $h
    $pl = NV $pts.plenos (NV $pts.partidos_procesados "OK")
    OK "Puntajes calculados ($pl plenos)"
} catch { ERR $_ }

# 6. Verificar bracket R32
Step "6. Bracket R32 resultante"
try {
    $br = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TID" -Headers $h
    $r32 = $br.partidos | Where-Object { $_.tipo -eq 'ronda32' }
    if (-not $r32) { $r32 = $br.partidos | Select-Object -First 16 }
    $con = ($r32 | Where-Object { $null -ne $_.local }).Count
    $sin = ($r32 | Where-Object { $null -eq $_.local }).Count
    Write-Host "  R32: $($r32.Count) partidos | Con equipo: $con | Sin equipo: $sin" `
        -ForegroundColor $(if ($sin -eq 0) { "Green" } else { "Yellow" })
    foreach ($p in $r32) {
        $loc = if ($p.local)     { $p.local.nombre }     else { "TBD" }
        $vis = if ($p.visitante) { $p.visitante.nombre } else { "TBD" }
        $col = if ($p.local -and $p.visitante) { "Green" } else { "DarkGray" }
        Write-Host ("    P{0,-3} {1,-24} vs {2}" -f $p.num, $loc, $vis) -ForegroundColor $col
    }
} catch { ERR $_ }

Write-Host ""
Write-Host "=== LISTO $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Magenta
Start-Sleep -Seconds 3
