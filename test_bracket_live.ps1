# Test: login + avanzar bracket + verificar bracket-real
$base = "http://localhost:8000"

Write-Host "=== 1. Login ===" -ForegroundColor Cyan
$login = Invoke-RestMethod -Uri "$base/api/v1/auth/login" -Method POST -ContentType "application/x-www-form-urlencoded" -Body "username=jose&password=catalina"
$token = $login.access_token
Write-Host "Token OK: $($token.Substring(0,20))..."

$headers = @{ Authorization = "Bearer $token" }

Write-Host "`n=== 2. Avanzar Bracket ===" -ForegroundColor Cyan
$avanzar = Invoke-RestMethod -Uri "$base/api/v1/bets/avanzar-bracket/2" -Method POST -Headers $headers
Write-Host "Avanzar OK: $($avanzar | ConvertTo-Json -Depth 2 | Select-Object -First 5)"

Write-Host "`n=== 3. Bracket Real - primeros 16avos ===" -ForegroundColor Cyan
$bracket = Invoke-RestMethod -Uri "$base/api/v1/bets/bracket-real/2" -Headers $headers
$ronda32 = $bracket.partidos | Where-Object { $_.tipo -eq "ronda32" }
Write-Host "Total KO partidos: $($bracket.partidos.Count)"
Write-Host "Ronda32 (16avos): $($ronda32.Count)"
foreach ($p in $ronda32 | Select-Object -First 4) {
    $l = if ($p.local) { "$($p.local.nombre) [$($p.local.iso)]" } else { "VACÍO" }
    $v = if ($p.visitante) { "$($p.visitante.nombre) [$($p.visitante.iso)]" } else { "VACÍO" }
    Write-Host "  P$($p.num): $l vs $v | fin=$($p.finalizado) | vivo=$($p.en_vivo)"
}

Write-Host "`n=== LISTO - Abrir: http://localhost:8000/static/becbuc-live.html ===" -ForegroundColor Green
Read-Host "Presiona Enter para salir"
