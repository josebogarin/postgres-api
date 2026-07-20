Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  FIX SWAP NUMERO FIFA - Adoptando numeracion Excel oficial" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Aplicando intercambio de numero_fifa para los 5 pares..." -ForegroundColor Yellow
Get-Content "C:\proyecto FAST API\documentacion\fix_swap_numero_fifa.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
Write-Host ""
Write-Host "Verificando que no hay temporales..." -ForegroundColor Yellow
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT numero_fifa, (SELECT nombre FROM equipo WHERE id=p.equipo_local_id) AS local, (SELECT nombre FROM equipo WHERE id=p.equipo_visitante_id) AS visitante FROM partido p WHERE numero_fifa IN (49,50,55,56,61,62,65,66,67,68) ORDER BY numero_fifa;"
