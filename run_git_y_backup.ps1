# run_git_y_backup.ps1
# Git commit + push + backup sesion 39

cd "C:\proyecto FAST API\backend"

Write-Host "=== Git status ===" -ForegroundColor Cyan
git status --short

Write-Host ""
Write-Host "=== Git add + commit ===" -ForegroundColor Cyan
git add -A
git commit -m "sesion 39: stats_fuentes tabla completa + ESPN matching mejorado + SofaScore deshabilitado

- partido_stats_fuentes: columnas api_*/espn_*/ss_* para amarillas/rojas/var/penales/minuto
- SOFASCORE_ENABLED=False (403 Forbidden desde servidor)
- ESPN matching: mapa ES->EN 90+ equipos + normalizacion de keys + fallback fecha -1 dia
- ESPN cobertura: 48% -> 100% (todos los 54 partidos finalizados matchean)
- populate_stats_fuentes_all: UPSERT completo con todas las columnas, fix fecha date object
- _sofascore_extract_stats: agrega extraccion minuto_primer_gol desde incidents
- Scripts: analizar_fuentes.py, cruzar_fuentes.py, diag_sync_estado.py, diag_sofascore.py
- Scripts ps1: run_populate_y_analisis.ps1, run_auto_mapeo.ps1, run_migrate_and_populate.ps1
- migracion_stats_fuentes.sql: v3 (numero_fifa, minuto_primer_gol) + v4 (api/espn/ss_minuto)"

Write-Host ""
Write-Host "=== Git push ===" -ForegroundColor Cyan
git push

Write-Host ""
Write-Host "=== Backup ===" -ForegroundColor Cyan
cd "C:\proyecto FAST API"
.\backup_becbuc.ps1

Write-Host ""
Write-Host "=== Listo ===" -ForegroundColor Green
Read-Host "Presiona Enter para cerrar"
