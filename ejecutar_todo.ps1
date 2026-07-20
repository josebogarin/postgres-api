# Script de actualizacion completa BECBUC
# 1. Fix minuto_primer_gol en partidos 0-0 (P14 y P45)
# 2. Recalcular puntajes via API
# 3. Verificar resultado cherem

$BASE = "http://localhost:8000"
$PROYECTO = "C:\proyecto FAST API"

Write-Host "=== ACTUALIZACION COMPLETA BECBUC ===" -ForegroundColor Cyan
Write-Host ""

# PASO 1: Fix minuto_primer_gol en partidos 0-0 (P14 y P45)
Write-Host "[1/3] Corrigiendo minuto_primer_gol en partidos 0-0..." -ForegroundColor Yellow
Get-Content "$PROYECTO\fix_minuto.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
Write-Host "Fix minuto aplicado." -ForegroundColor Green
Write-Host ""

# PASO 2: Login y recalcular puntajes
Write-Host "[2/3] Recalculando puntajes (necesita servidor activo en puerto 8000)..." -ForegroundColor Yellow
try {
    $loginBody = '{"username":"jose","password":"catalina"}'
    $login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -ContentType "application/json" -Body $loginBody -TimeoutSec 10
    $token = $login.access_token
    Write-Host "Login OK." -ForegroundColor Green

    $headers = @{ Authorization = "Bearer $token" }
    $recalc = Invoke-RestMethod -Uri "$BASE/api/v1/bets/calcular-puntajes/2" -Method Post -Headers $headers -TimeoutSec 60
    Write-Host "Recalculo completado:" -ForegroundColor Green
    Write-Host "  Procesados: $($recalc.procesados)"
    Write-Host "  Plenos (marcador exacto): $($recalc.plenos)"
    Write-Host "  Aciertos (resultado): $($recalc.aciertos)"
    Write-Host "  Fallos: $($recalc.fallos)"
} catch {
    Write-Host "ERROR en recalculo: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "ATENCION: Inicia el servidor uvicorn y luego corre recalc_api.ps1 manualmente."
    Write-Host "cd 'C:\proyecto FAST API\backend' && .venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"
}
Write-Host ""

# PASO 3: Verificar puntajes de cherem
Write-Host "[3/3] Verificando puntajes de cherem..." -ForegroundColor Yellow
Get-Content "$PROYECTO\verify_cherem.sql" | docker exec -i core-postgres psql -U app_user -d becbuc | Tee-Object "$PROYECTO\verify_final.txt"

Write-Host ""
Write-Host "=== RESUMEN DIFFs (lineas con ***DIFF) ===" -ForegroundColor Cyan
$content = Get-Content "$PROYECTO\verify_final.txt" -ErrorAction SilentlyContinue
$diffs = $content | Where-Object { $_ -match "DIFF" }
if ($diffs) {
    $diffs | ForEach-Object { Write-Host $_ -ForegroundColor Red }
    Write-Host ""
    Write-Host "Total lineas con DIFF: $($diffs.Count)" -ForegroundColor Red
} else {
    Write-Host "SIN diferencias - puntajes 100% correctos!" -ForegroundColor Green
}

Write-Host ""
Read-Host "Presiona Enter para salir"
