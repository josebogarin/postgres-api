@echo off
echo ============================================================
echo  DIAGNOSTICO BRACKET - Estado partidos KO en la BD
echo ============================================================
echo.

docker exec core-postgres psql -U app_user -d becbuc -c ^
"SELECT p.numero, ^
       TO_CHAR(p.fecha AT TIME ZONE 'UTC', 'DD Mon HH24:MI') AS fecha_utc, ^
       f.tipo AS fase, ^
       p.estado, ^
       COALESCE(el.nombre_es, el.nombre, '??? TBD') AS local, ^
       COALESCE(ev.nombre_es, ev.nombre, '??? TBD') AS visitante, ^
       CASE WHEN p.goles_local IS NOT NULL THEN p.goles_local::text ELSE '-' END AS gl, ^
       CASE WHEN p.goles_visitante IS NOT NULL THEN p.goles_visitante::text ELSE '-' END AS gv ^
 FROM partido p ^
 JOIN fase f ON f.id = p.fase_id ^
 LEFT JOIN equipo el ON el.id = p.equipo_local_id ^
 LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id ^
 WHERE p.torneo_id = 2 AND f.tipo <> 'grupo' ^
 ORDER BY p.numero;"

echo.
echo ============================================================
echo  RESUMEN TBD vs confirmados
echo ============================================================
docker exec core-postgres psql -U app_user -d becbuc -c ^
"SELECT f.tipo AS fase, ^
       COUNT(*) AS total, ^
       COUNT(p.equipo_local_id) AS con_local, ^
       COUNT(p.equipo_visitante_id) AS con_visitante, ^
       COUNT(CASE WHEN p.estado='finalizado' THEN 1 END) AS finalizados ^
 FROM partido p ^
 JOIN fase f ON f.id = p.fase_id ^
 WHERE p.torneo_id = 2 AND f.tipo <> 'grupo' ^
 GROUP BY f.tipo ^
 ORDER BY MIN(p.numero);"

echo.
pause
