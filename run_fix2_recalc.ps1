$BASE = "http://localhost:8000"
$PROYECTO = "C:\proyecto FAST API"

Write-Host "Paso 1: Fix minuto P34/P39/P60..."
Get-Content "$PROYECTO\fix_minuto2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

Write-Host "Paso 2: Recalculando puntajes..."
try {
    $login = Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}' -TimeoutSec 8
    $headers = @{ Authorization = "Bearer $($login.access_token)" }
    $r = Invoke-RestMethod -Uri "$BASE/api/v1/bets/calcular-puntajes/2" -Method Post -Headers $headers -TimeoutSec 60
    Write-Host "Recalculo OK - plenos=$($r.plenos) aciertos=$($r.aciertos)"
} catch { Write-Host "ERROR: $_" }

Write-Host "Paso 3: Verificacion global todos los apostadores..."
Get-Content "$PROYECTO\verify_todos.sql" | docker exec -i core-postgres psql -U app_user -d becbuc | Out-File "$PROYECTO\verify_todos2.txt" -Encoding UTF8

$content = Get-Content "$PROYECTO\verify_todos2.txt" -ErrorAction SilentlyContinue
$diffs = $content | Where-Object { $_ -match "DIFFS" }
Write-Host ""
Write-Host "=== APOSTADORES CON DIFFS ==="
if ($diffs) { $diffs | ForEach-Object { Write-Host $_ } }
else { Write-Host "NINGUNO - todos OK!" }
