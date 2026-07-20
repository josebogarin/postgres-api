# Script de comparacion de puntajes BECBUC vs tabla imagen
$query = @"
SELECT 
  COALESCE(u.nombre, u.username) AS alias,
  COALESCE(SUM(pd.pts_resultado),0)::INT AS H,
  COALESCE(SUM(pd.pts_marcador),0)::INT AS I,
  COALESCE(SUM(pd.pts_amarillas),0)::INT AS J,
  COALESCE(SUM(pd.pts_rojas),0)::INT AS K,
  COALESCE(SUM(pd.pts_var),0)::INT AS L,
  COALESCE(SUM(pd.pts_penales_partido),0)::INT AS M,
  COALESCE(SUM(pd.pts_minuto),0)::INT AS N,
  COALESCE(SUM(pd.pts_penales_tanda),0)::INT AS O,
  COALESCE(SUM(pd.pts_resultado+pd.pts_marcador+pd.pts_amarillas+pd.pts_rojas+pd.pts_var+pd.pts_penales_partido+pd.pts_minuto+pd.pts_penales_tanda),0)::INT AS total_partidos,
  COALESCE(pg2.pts_total,0)::INT AS globales,
  (COALESCE(SUM(pd.pts_resultado+pd.pts_marcador+pd.pts_amarillas+pd.pts_rojas+pd.pts_var+pd.pts_penales_partido+pd.pts_minuto+pd.pts_penales_tanda),0)+COALESCE(pg2.pts_total,0))::INT AS TOTAL
FROM puntaje_detalle pd
JOIN (
  SELECT id, COALESCE(nombre, username) as nombre, username FROM dblink('hostaddr=localhost port=5432 dbname=app_db user=app_user password=', 'SELECT id, nombre, username FROM users') AS t(id INT, nombre VARCHAR, username VARCHAR)
) u ON pd.apostador_id = u.id
LEFT JOIN (
  SELECT apostador_id, SUM(COALESCE(pts_campeon,0)+COALESCE(pts_finalistas,0)+COALESCE(pts_goleador,0)+COALESCE(pts_peor_equipo,0)+COALESCE(pts_mayor_goleada,0)+COALESCE(pts_etapa_paraguay,0)+COALESCE(pts_goles_paraguay,0))::INT AS pts_total
  FROM puntaje_global WHERE torneo_id=2
  GROUP BY apostador_id
) pg2 ON pd.apostador_id = pg2.apostador_id
WHERE pd.torneo_id = 2
GROUP BY u.nombre, u.username, pg2.pts_total
ORDER BY TOTAL DESC;
"@

$result = $query | docker exec -i core-postgres psql -U app_user -d becbuc -t -A -F ","
$result | Out-File "C:\proyecto FAST API\becbuc_scores.csv" -Encoding UTF8
Write-Host "Guardado en becbuc_scores.csv"
$result | Select-Object -First 20
