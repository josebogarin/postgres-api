# Recalcula standings + mejores terceros + bracket con el nuevo criterio FIFA
# El servidor debe estar corriendo (uvicorn port 8000)

$base = "http://localhost:8000/api/v1"

Write-Host "=== Recalc Mejores Terceros (criterio FIFA PJ completo) ===" -ForegroundColor Cyan

# Login
$tok = (Invoke-RestMethod "$base/auth/login" -Method POST -ContentType "application/json" `
    -Body '{"username":"jose","password":"catalina"}').access_token
if (-not $tok) { Write-Host "Login fallido" -ForegroundColor Red; exit 1 }
$h = @{ Authorization = "Bearer $tok" }
Write-Host "✓ Login OK" -ForegroundColor Green

# Recalcular participacion (standings reales)
Write-Host "`nRecalculando puntajes y bracket..." -ForegroundColor Yellow
$r = Invoke-RestMethod "$base/bets/calcular-puntajes/2" -Method POST -Headers $h
Write-Host "  ✓ Puntajes: $($r.procesados) apostadores" -ForegroundColor Green

# Avanzar bracket con los nuevos standings
$b = Invoke-RestMethod "$base/bets/avanzar-bracket/2" -Method POST -Headers $h
Write-Host "  ✓ Bracket: $($b.mensaje)" -ForegroundColor Green

# Ver resultado de mejores terceros
Write-Host "`n=== Mejores Terceros actuales ===" -ForegroundColor Cyan
try {
    $mt = Invoke-RestMethod "$base/bets/mejores-terceros-provisorios/2" -Headers $h
    Write-Host "Grupos completos: $($mt.grupos_completos) / $($mt.grupos_totales)" -ForegroundColor White
    Write-Host "`nCLASIFICADOS (mejores 8):" -ForegroundColor Green
    foreach ($t in $mt.clasificados) {
        $fp = $t.fair_play_pts
        Write-Host ("  [{0}] {1,-25} Pts:{2} DG:{3} GF:{4} FP:{5}" -f $t.grupo, $t.nombre, $t.pts, $t.gd, $t.gf, $fp)
    }
    if ($mt.eliminados.Count -gt 0) {
        Write-Host "`nELIMINADOS:" -ForegroundColor Red
        foreach ($t in $mt.eliminados) {
            Write-Host ("  [{0}] {1,-25} Pts:{2} DG:{3} GF:{4} FP:{5}" -f $t.grupo, $t.nombre, $t.pts, $t.gd, $t.gf, $t.fair_play_pts)
        }
    }
} catch {
    Write-Host "  (endpoint mejores-terceros no disponible: $_)" -ForegroundColor Yellow
}

Write-Host "`n=== LISTO ===" -ForegroundColor Cyan
Read-Host "Presioná Enter para cerrar"
