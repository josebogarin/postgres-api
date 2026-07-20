# sincronizar_final_grupos.ps1
# Cierre fase de grupos: sync API + bracket + cruces oficiales + puntajes
# Compatible PowerShell 5

$BASE   = "http://localhost:8000"
$TID    = 2
$PYTHON = "C:\proyecto FAST API\backend\.venv\Scripts\python.exe"

function Step($msg) { Write-Host ""; Write-Host ">>> $msg" -ForegroundColor Cyan }
function OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function WARN($msg) { Write-Host "    WARN: $msg" -ForegroundColor Yellow }
function ERR($msg)  { Write-Host "    ERROR: $msg" -ForegroundColor Red }
function NV($val, $def) { if ($null -ne $val) { $val } else { $def } }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " BECBUC - Cierre Fase de Grupos" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# -- 1. Login ---------------------------------------------------------------
Step "1. Login"
try {
    $body = '{"username":"jose","password":"catalina"}'
    $t = (Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/auth/login" `
        -ContentType "application/json" -Body $body).access_token
    if (-not $t) { throw "Token vacio" }
    OK "Autenticado"
} catch { ERR $_; Read-Host "Presiona Enter para salir"; exit 1 }

$h = @{ "Authorization" = "Bearer $t" }

# -- 2. Sync desde API-Football (fuerza todos los partidos) -----------------
Step "2. Sync desde API-Football (force=true)"
try {
    $s = Invoke-RestMethod -Method POST `
        -Uri "${BASE}/api/v1/bets/sync-resultados/${TID}?force=true&max_detalle=50" `
        -Headers $h
    $act = NV $s.actualizados 0
    OK "$act partido(s) actualizados"
    if ($s.error) { WARN $s.error }
} catch { WARN "Sync no disponible o sin cambios nuevos: $_" }

# -- 3. Verificar estado de grupos ------------------------------------------
Step "3. Verificar grupos finalizados"
try {
    $g = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/grupos/$TID" -Headers $h
    $totalT = 0; $totalF = 0; $grupos_pend = 0
    foreach ($f in $g.fases) {
        $fn = ($f.partidos | Where-Object { $_.estado -eq "finalizado" }).Count
        $tp = $f.partidos.Count
        $totalT += $tp; $totalF += $fn
        if ($fn -lt $tp) {
            $grupos_pend++
            WARN "Fase '$($f.nombre)': $fn/$tp finalizados"
        }
    }
    Write-Host "    Total: $totalF / $totalT partidos finalizados" -ForegroundColor White
    if ($grupos_pend -eq 0) { OK "Todos los grupos completados" }
} catch { WARN "No se pudo leer grupos: $_" }

# -- 4. Avanzar bracket (standings finales -> R32) --------------------------
Step "4. Avanzar bracket con standings finales"
try {
    $r = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/avanzar-bracket/$TID" -Headers $h
    OK "Bracket avanzado"
} catch { ERR "Avanzar bracket: $_" }

# -- 5. Aplicar cruces oficiales R32 ----------------------------------------
Step "5. Aplicar cruces oficiales R32 (P73-P88)"
Write-Host "    Ejecutando fix_r32_oficial.py con confirmacion automatica..." -ForegroundColor White
try {
    $pyScript = "C:\proyecto FAST API\fix_r32_oficial.py"
    $output = "s" | & $PYTHON $pyScript 2>&1
    foreach ($line in $output) {
        Write-Host "    $line" -ForegroundColor White
    }
    OK "Cruces R32 procesados"
} catch { WARN "fix_r32: $_" }

# -- 6. Calcular puntajes finales de grupos ---------------------------------
Step "6. Calcular puntajes (todos los grupos)"
try {
    $pts = Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/bets/calcular-puntajes/$TID" -Headers $h
    $pl  = NV $pts.plenos (NV $pts.partidos_procesados "?")
    $glb = NV $pts.globales_procesadas 0
    OK "Puntajes calculados: $pl plenos | $glb globales"
} catch { ERR "Calcular puntajes: $_" }

# -- 7. Bracket R32 resultante ----------------------------------------------
Step "7. Bracket R32 resultante"
try {
    $br  = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TID" -Headers $h
    $r32 = $br.partidos | Where-Object { $_.tipo -eq "ronda32" }
    if (-not $r32) { $r32 = $br.partidos | Select-Object -First 16 }
    $con = ($r32 | Where-Object { $null -ne $_.local }).Count
    $sin = ($r32 | Where-Object { $null -eq $_.local }).Count
    Write-Host ("    {0} partidos | Con equipo: {1} | Sin equipo: {2}" -f $r32.Count, $con, $sin) -ForegroundColor White
    foreach ($p in $r32 | Sort-Object num) {
        $loc = if ($p.local)     { $p.local.nombre }     else { "? TBD" }
        $vis = if ($p.visitante) { $p.visitante.nombre } else { "? TBD" }
        $col = if ($p.local -and $p.visitante) { "White" } else { "DarkGray" }
        Write-Host ("    P{0,-3} {1,-26} vs {2}" -f $p.num, $loc, $vis) -ForegroundColor $col
    }
} catch { ERR "Bracket: $_" }

# -- 8. Top 5 ranking -------------------------------------------------------
Step "8. Top 5 Ranking"
try {
    $rk  = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/ranking/$TID" -Headers $h
    $top = $rk.ranking | Select-Object -First 5
    $pos = 1
    foreach ($r in $top) {
        $pts2 = NV $r.puntos_total (NV $r.puntos 0)
        Write-Host ("    {0}. {1,-22} {2} pts" -f $pos, $r.nombre, $pts2) -ForegroundColor Cyan
        $pos++
    }
} catch { WARN "Ranking no disponible: $_" }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " LISTO" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""

Read-Host "Presiona Enter para cerrar"
