# Recalcular puntajes post-update excel
$base = "http://localhost:8000/api/v1"
$tok = (Invoke-RestMethod "$base/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}').access_token
$h = @{ Authorization = "Bearer $tok" }
Write-Host "Recalculando puntajes..." -ForegroundColor Yellow
$r = Invoke-RestMethod "$base/bets/calcular-puntajes/2" -Method POST -Headers $h -TimeoutSec 120
Write-Host "Procesados: $($r.procesados) apostadores" -ForegroundColor Green
Write-Host "Listo. Presioná Enter para cerrar."
Read-Host
