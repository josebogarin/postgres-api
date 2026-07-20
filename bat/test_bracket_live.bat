@echo off
cd /d "C:\proyecto FAST API"
powershell -NoProfile -ExecutionPolicy Bypass -Command "
$base = 'http://localhost:8000'
Write-Host '=== Login ===' -ForegroundColor Cyan
$login = Invoke-RestMethod -Uri \"$base/api/v1/auth/login\" -Method POST -ContentType 'application/x-www-form-urlencoded' -Body 'username=jose&password=catalina'
$token = \$login.access_token
\$headers = @{ Authorization = \"Bearer \$token\" }

Write-Host '=== Avanzar Bracket ===' -ForegroundColor Cyan
\$av = Invoke-RestMethod -Uri \"$base/api/v1/bets/avanzar-bracket/2\" -Method POST -Headers \$headers
Write-Host (\$av | ConvertTo-Json -Depth 2)

Write-Host '=== Bracket Real ===' -ForegroundColor Cyan
\$br = Invoke-RestMethod -Uri \"$base/api/v1/bets/bracket-real/2\" -Headers \$headers
\$r32 = \$br.partidos | Where-Object { \$_.tipo -eq 'ronda32' }
Write-Host \"Total KO: \$(\$br.partidos.Count) | ronda32: \$(\$r32.Count)\"
\$r32 | Select-Object -First 8 | ForEach-Object {
    \$l = if (\$_.local) { \"\$(\$_.local.nombre)[\$(\$_.local.iso)]\" } else { 'VACIO' }
    \$v = if (\$_.visitante) { \"\$(\$_.visitante.nombre)[\$(\$_.visitante.iso)]\" } else { 'VACIO' }
    Write-Host \"  P\$(\$_.num): \$l vs \$v\"
}
Write-Host '=== Abriendo Chrome ===' -ForegroundColor Green
Start-Process 'http://localhost:8000/static/becbuc-live.html'
"
pause
