# Post-fix Paraguay: recalcular puntajes + avanzar bracket con standings correctos
$base = "http://localhost:8000/api/v1"
Write-Host "=== Post-fix Paraguay ===" -ForegroundColor Cyan

$tok = (Invoke-RestMethod "$base/auth/login" -Method POST -ContentType "application/json" `
    -Body '{"username":"jose","password":"catalina"}').access_token
if (-not $tok) { Write-Host "Login fallido" -ForegroundColor Red; exit 1 }
$h = @{ Authorization = "Bearer $tok" }
Write-Host "✓ Login OK" -ForegroundColor Green

Write-Host "`n[1/3] Recalculando puntajes..." -ForegroundColor Yellow
try {
    $r = Invoke-RestMethod "$base/bets/calcular-puntajes/2" -Method POST -Headers $h -TimeoutSec 120
    Write-Host "  ✓ Procesados: $($r.procesados) apostadores" -ForegroundColor Green
} catch { Write-Host "  WARNING: $($_.Exception.Message)" -ForegroundColor Yellow }

Write-Host "`n[2/3] Avanzando bracket (actualiza mejores terceros)..." -ForegroundColor Yellow
$b = Invoke-RestMethod "$base/bets/avanzar-bracket/2" -Method POST -Headers $h
Write-Host "  ✓ $($b.mensaje)" -ForegroundColor Green

Write-Host "`n[3/3] Verificando mejores terceros..." -ForegroundColor Yellow
try {
    $mt = Invoke-RestMethod "$base/bets/mejores-terceros-provisorios/2" -Headers $h
    Write-Host "  Grupos completos: $($mt.grupos_completos) / $($mt.grupos_totales)" -ForegroundColor White
    Write-Host "`n  CLASIFICADOS (8):" -ForegroundColor Green
    foreach ($t in $mt.clasificados) {
        $py = if ($t.nombre -match 'Parag') { " <-- PARAGUAY ✓" } else { "" }
        Write-Host ("    [{0}] {1,-28} Pts:{2} DG:{3:+0} GF:{4} PJ:{5}{6}" -f $t.grupo, $t.nombre, $t.pts, $t.gd, $t.gf, $t.pj, $py) -ForegroundColor $(if ($py) { 'Cyan' } else { 'White' })
    }
    if ($mt.eliminados.Count -gt 0) {
        Write-Host "`n  ELIMINADOS:" -ForegroundColor Red
        foreach ($t in $mt.eliminados) {
            $py = if ($t.nombre -match 'Parag') { " <-- PARAGUAY" } else { "" }
            Write-Host ("    [{0}] {1,-28} Pts:{2} DG:{3:+0} GF:{4} PJ:{5}{6}" -f $t.grupo, $t.nombre, $t.pts, $t.gd, $t.gf, $t.pj, $py)
        }
    }
} catch { Write-Host "  (endpoint no disponible: $_)" -ForegroundColor Yellow }

Write-Host "`n=== LISTO ===" -ForegroundColor Cyan
Read-Host "Presioná Enter para cerrar"
