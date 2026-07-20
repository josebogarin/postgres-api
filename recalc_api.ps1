# Recalcular puntajes via API
$BASE = "http://localhost:8000"

# Login
try {
    $login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}'
    $token = $login.access_token
    Write-Host "Login OK. Token obtenido."
} catch {
    Write-Host "ERROR en login: $_"
    Write-Host "Verificar que el servidor uvicorn este corriendo en puerto 8000"
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Recalcular puntajes
$headers = @{ Authorization = "Bearer $token" }
try {
    $r = Invoke-RestMethod -Uri "$BASE/api/v1/bets/calcular-puntajes/2" -Method Post -Headers $headers
    Write-Host "Recalculo OK!"
    Write-Host "Procesados: $($r.procesados)"
    Write-Host "Plenos: $($r.plenos)"
    Write-Host "Aciertos: $($r.aciertos)"
} catch {
    Write-Host "ERROR en recalculo: $_"
}

Read-Host "Presiona Enter para salir"
