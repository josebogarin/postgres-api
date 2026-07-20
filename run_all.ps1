# Script silencioso - escribe todo al log
$PROYECTO = "C:\proyecto FAST API"
$LOG = "$PROYECTO\run_all_log.txt"

"=== BECBUC ACTUALIZACION $(Get-Date) ===" | Out-File $LOG -Encoding UTF8

# PASO 1: Fix minuto_primer_gol en partidos 0-0
"[1/3] Fix minuto_primer_gol en P14/P45..." | Tee-Object $LOG -Append
Get-Content "$PROYECTO\fix_minuto.sql" | docker exec -i core-postgres psql -U app_user -d becbuc 2>&1 | Tee-Object $LOG -Append

# PASO 2: Recalcular puntajes
"[2/3] Recalculando puntajes..." | Tee-Object $LOG -Append
try {
    $login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}' -TimeoutSec 8
    $token = $login.access_token
    $headers = @{ Authorization = "Bearer $token" }
    $r = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/bets/calcular-puntajes/2" -Method Post -Headers $headers -TimeoutSec 60
    "OK - procesados=$($r.procesados) plenos=$($r.plenos) aciertos=$($r.aciertos)" | Tee-Object $LOG -Append
} catch {
    "ERROR recalculo: $_" | Tee-Object $LOG -Append
    "ATENCION: Inicia uvicorn y corre recalc_api.ps1 por separado" | Tee-Object $LOG -Append
}

# PASO 3: Verificar cherem
"[3/3] Verificando puntajes cherem..." | Tee-Object $LOG -Append
Get-Content "$PROYECTO\verify_cherem.sql" | docker exec -i core-postgres psql -U app_user -d becbuc 2>&1 | Tee-Object $LOG -Append | Out-File "$PROYECTO\verify_final.txt" -Encoding UTF8

# Resumen DIFFs
"" | Out-File $LOG -Append
"=== DIFFS ===" | Out-File $LOG -Append
$diffs = Get-Content "$PROYECTO\verify_final.txt" -ErrorAction SilentlyContinue | Where-Object { $_ -match "DIFF" }
if ($diffs) {
    $diffs | Tee-Object $LOG -Append
    "TOTAL DIFFS: $($diffs.Count)" | Tee-Object $LOG -Append
} else {
    "SIN DIFFS - puntajes 100% correctos!" | Tee-Object $LOG -Append
}

"=== FIN ===" | Out-File $LOG -Append
