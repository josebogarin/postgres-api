# check_r32.ps1 - Solo verifica bracket R32
$BASE = "http://localhost:8000"
$TID  = 2

Write-Host "=== Verificando R32 ===" -ForegroundColor Cyan
try {
    $t = (Invoke-RestMethod -Method POST -Uri "$BASE/api/v1/auth/login" `
        -ContentType "application/json" `
        -Body '{"username":"jose","password":"catalina"}').access_token

    $br = Invoke-RestMethod -Method GET -Uri "$BASE/api/v1/bets/bracket-real/$TID" `
        -Headers @{ Authorization = "Bearer $t" }

    $all = $br.partidos
    $r32 = $all | Where-Object { $_.tipo -eq 'ronda32' }
    if (-not $r32) { $r32 = $all | Select-Object -First 16 }

    $con = ($r32 | Where-Object { $null -ne $_.local }).Count
    $sin = ($r32 | Where-Object { $null -eq $_.local }).Count

    Write-Host ("R32: {0} partidos | Con equipo: {1} | Sin equipo: {2}" -f $r32.Count, $con, $sin) `
        -ForegroundColor $(if ($sin -eq 0) { "Green" } else { "Yellow" })
    Write-Host ""
    foreach ($p in $r32 | Sort-Object num) {
        $loc = if ($p.local)     { $p.local.nombre }     else { "TBD" }
        $vis = if ($p.visitante) { $p.visitante.nombre } else { "TBD" }
        $col = if ($p.local -and $p.visitante) { "Green" } else { "DarkGray" }
        $fin = if ($p.finalizado) { " [FIN {0}-{1}]" -f $p.goles_local, $p.goles_visitante } else { "" }
        Write-Host ("  P{0,-3} {1,-24} vs {2}{3}" -f $p.num, $loc, $vis, $fin) -ForegroundColor $col
    }
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}

Write-Host ""
Read-Host "Presiona Enter para cerrar"
