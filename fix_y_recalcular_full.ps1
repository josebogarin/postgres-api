# BECBUC - Fix VAR Canada/Qatar + Recálculo completo
# Ejecutar como: powershell -ExecutionPolicy Bypass -File fix_y_recalcular_full.ps1
$ErrorActionPreference = "Continue"
$proj = "C:\proyecto FAST API"
$base = "http://localhost:8000"

Write-Host "`n=== BECBUC Fix + Recálculo ===" -ForegroundColor Cyan

# 1. Fix Canada vs Qatar
Write-Host "`n[1/3] Corrigiendo Canada vs Qatar decisiones_var=2..." -ForegroundColor Yellow
$sql = @"
UPDATE partido SET decisiones_var=2 
WHERE id=(
  SELECT p.id FROM partido p 
  JOIN equipo el ON el.id=p.equipo_local_id 
  JOIN equipo ev ON ev.id=p.equipo_visitante_id 
  WHERE (LOWER(el.nombre) LIKE '%canad%' AND LOWER(ev.nombre) LIKE '%qatar%')
     OR (LOWER(ev.nombre) LIKE '%canad%' AND LOWER(el.nombre) LIKE '%qatar%')
  LIMIT 1
);
"@
docker exec core-postgres psql -U app_user -d becbuc -c $sql
Write-Host "  OK" -ForegroundColor Green

# 2. Login
Write-Host "`n[2/3] Login..." -ForegroundColor Yellow
$login = Invoke-RestMethod -Method POST -Uri "$base/api/v1/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"jose","password":"catalina"}'
$tok = $login.access_token
$headers = @{ Authorization = "Bearer $tok" }
Write-Host "  Token OK" -ForegroundColor Green

# 3. Recalcular
Write-Host "`n[3/3] Recalculando puntajes..." -ForegroundColor Yellow
$r = Invoke-RestMethod -Method POST -Uri "$base/api/v1/bets/calcular-puntajes/2" -Headers $headers
Write-Host "  Procesados: $($r.procesados) partidos, $($r.puntajes_procesados) puntajes" -ForegroundColor Green

# 4. Top5
Write-Host "`nTop 5 ranking actual:" -ForegroundColor Cyan
$rank = Invoke-RestMethod -Uri "$base/api/v1/bets/ranking/2" -Headers $headers
$rank | Select-Object -First 5 | ForEach-Object {
  Write-Host "  $($_.nombre): $($_.puntos_total) pts (VAR=$($_.cat_var), Amar=$($_.cat_amarillas))"
}
Write-Host "`n=== LISTO - Recarga becbuc-live.html ===" -ForegroundColor Green
