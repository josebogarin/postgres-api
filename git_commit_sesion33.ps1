# Sesion 33 - commit rapido
# Ejecutar desde: C:\proyecto FAST API

cd "C:\proyecto FAST API\backend"

# Limpiar lock si existe
if (Test-Path ".git\index.lock") { Remove-Item ".git\index.lock" -Force }

git add -A
git commit -m "sesion 33: live-panel fix (numero_fifa + apuestas query) + espn_verify restaurado + tabs partido/ranking becbuc-live"
git push

Write-Host "`n=== COMMIT OK ===" -ForegroundColor Green
