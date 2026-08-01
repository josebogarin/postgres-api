@echo off
echo Comparando pronosticos_aux vs apuesta (todos los apostadores, grupos)... > "%~dp0..\todos_diffs.txt"
docker exec core-postgres psql -U app_user -d becbuc -t -A -F"|" -c "
SELECT
    pa.nombre,
    pa.alias,
    p.numero_fifa,
    pa.goles_local AS excel_l,
    pa.goles_visitante AS excel_v,
    a.pred_local AS bd_l,
    a.pred_visitante AS bd_v
FROM pronosticos_aux pa
JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa
JOIN apuesta a ON a.partido_id = p.id
JOIN fase f ON f.id = p.fase_id
JOIN dblink('dbname=app_db user=app_user', 'SELECT id, username, nombre FROM users') AS u(uid INT, username TEXT, nombre TEXT)
    ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
    AND a.apostador_id = u.uid
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND p.estado = 'finalizado'
  AND (pa.goles_local != a.pred_local OR pa.goles_visitante != a.pred_visitante)
ORDER BY pa.nombre, p.numero_fifa;
" >> "%~dp0..\todos_diffs.txt" 2>&1

echo. >> "%~dp0..\todos_diffs.txt"
echo === RESUMEN: diferencias por apostador === >> "%~dp0..\todos_diffs.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    pa.nombre,
    pa.alias,
    COUNT(*) AS partidos_diferentes
FROM pronosticos_aux pa
JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa
JOIN apuesta a ON a.partido_id = p.id
JOIN fase f ON f.id = p.fase_id
JOIN dblink('dbname=app_db user=app_user', 'SELECT id, username, nombre FROM users') AS u(uid INT, username TEXT, nombre TEXT)
    ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
    AND a.apostador_id = u.uid
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND p.estado = 'finalizado'
  AND (pa.goles_local != a.pred_local OR pa.goles_visitante != a.pred_visitante)
GROUP BY pa.nombre, pa.alias
ORDER BY partidos_diferentes DESC, pa.nombre;
" >> "%~dp0..\todos_diffs.txt" 2>&1

echo. >> "%~dp0..\todos_diffs.txt"
echo === TOTAL apostadores con diferencias === >> "%~dp0..\todos_diffs.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT COUNT(DISTINCT pa.nombre) AS apostadores_con_diff,
       COUNT(*) AS total_diferencias
FROM pronosticos_aux pa
JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa
JOIN apuesta a ON a.partido_id = p.id
JOIN fase f ON f.id = p.fase_id
JOIN dblink('dbname=app_db user=app_user', 'SELECT id, username, nombre FROM users') AS u(uid INT, username TEXT, nombre TEXT)
    ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
    AND a.apostador_id = u.uid
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND p.estado = 'finalizado'
  AND (pa.goles_local != a.pred_local OR pa.goles_visitante != a.pred_visitante);
" >> "%~dp0..\todos_diffs.txt" 2>&1

type "%~dp0..\todos_diffs.txt"
pause
