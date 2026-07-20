@echo off
echo === Cobertura del join pronosticos_aux vs apuesta === > "C:\proyecto FAST API\cobertura.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    COUNT(DISTINCT pa.nombre) AS apostadores_en_aux,
    COUNT(DISTINCT u.uid) AS apostadores_con_match,
    COUNT(*) AS filas_comparadas
FROM pronosticos_aux pa
JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa
JOIN apuesta a ON a.partido_id = p.id
JOIN fase f ON f.id = p.fase_id
JOIN dblink('dbname=app_db user=app_user', 'SELECT id, username, nombre FROM users') AS u(uid INT, username TEXT, nombre TEXT)
    ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
    AND a.apostador_id = u.uid
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND p.estado = 'finalizado';
" >> "C:\proyecto FAST API\cobertura.txt" 2>&1

echo. >> "C:\proyecto FAST API\cobertura.txt"
echo === Apostadores en pronosticos_aux SIN match en app_db === >> "C:\proyecto FAST API\cobertura.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT DISTINCT pa.nombre, pa.alias
FROM pronosticos_aux pa
WHERE NOT EXISTS (
    SELECT 1
    FROM dblink('dbname=app_db user=app_user', 'SELECT id, nombre FROM users') AS u(uid INT, nombre TEXT)
    WHERE LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
)
ORDER BY pa.nombre;
" >> "C:\proyecto FAST API\cobertura.txt" 2>&1

echo. >> "C:\proyecto FAST API\cobertura.txt"
echo === Apostadores SIN diferencias (match completo) === >> "C:\proyecto FAST API\cobertura.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    pa.nombre, pa.alias,
    COUNT(*) AS partidos_iguales
FROM pronosticos_aux pa
JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa
JOIN apuesta a ON a.partido_id = p.id
JOIN fase f ON f.id = p.fase_id
JOIN dblink('dbname=app_db user=app_user', 'SELECT id, nombre FROM users') AS u(uid INT, nombre TEXT)
    ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre))
    AND a.apostador_id = u.uid
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND p.estado = 'finalizado'
  AND pa.goles_local = a.pred_local
  AND pa.goles_visitante = a.pred_visitante
GROUP BY pa.nombre, pa.alias
ORDER BY pa.nombre;
" >> "C:\proyecto FAST API\cobertura.txt" 2>&1

type "C:\proyecto FAST API\cobertura.txt"
pause
