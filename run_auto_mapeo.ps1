# run_auto_mapeo.ps1
# Mapea los partidos KO faltantes contra API-Football

cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\Activate.ps1
cd "C:\proyecto FAST API"

Write-Host "=== Login ===" -ForegroundColor Cyan
$loginBody = '{"username":"jose","password":"catalina"}'
$loginResp = irm "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/json" -Body $loginBody
$tok = $loginResp.access_token
Write-Host "Token OK" -ForegroundColor Green

Write-Host ""
Write-Host "=== Auto-mapeo fixtures API-Football ===" -ForegroundColor Cyan
$result = irm "http://localhost:8000/api/v1/bets/api-mapeo/2/auto" -Method POST -Headers @{Authorization="Bearer $tok"}
Write-Host "Resultado:" -ForegroundColor Green
$result | ConvertTo-Json -Depth 3

Write-Host ""
Write-Host "=== Verificando estado post-mapeo ===" -ForegroundColor Cyan
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost',port=5432,dbname='becbuc',user='app_user',password='app_password')
cur = conn.cursor()
cur.execute('''SELECT COUNT(*) FILTER (WHERE api_fixture_id IS NOT NULL) AS mapeados, COUNT(*) AS total FROM partido WHERE torneo_id=2''')
m, t = cur.fetchone()
print(f'  Partidos mapeados: {m}/{t} ({100*m//t}%)')
cur.execute('''SELECT p.numero_fifa, COALESCE(el.nombre_es,el.nombre) as loc, COALESCE(ev.nombre_es,ev.nombre) as vis FROM partido p LEFT JOIN equipo el ON el.id=p.equipo_local_id LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id WHERE p.torneo_id=2 AND p.api_fixture_id IS NULL ORDER BY p.numero_fifa NULLS LAST''')
rows = cur.fetchall()
if rows:
    print(f'  Sin mapear ({len(rows)}):')
    for r in rows: print(f'    P{r[0]}  {r[1]} vs {r[2]}')
else:
    print('  Todos los partidos mapeados!')
conn.close()
"

Read-Host "Presiona Enter para cerrar"
