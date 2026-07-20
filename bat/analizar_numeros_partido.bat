@echo off
echo Analizando discrepancias de numero_partido en BD...

docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    p.id            AS db_id,
    p.numero_fifa   AS num_fifa,
    CASE WHEN p.numero_fifa IS NULL THEN 'SIN num_fifa'
         WHEN p.id = p.numero_fifa THEN 'ok'
         ELSE 'DISCREPANCIA'
    END AS estado,
    e1.nombre       AS local,
    e2.nombre       AS visitante,
    f.grupo         AS grupo
FROM partido p
JOIN equipo e1 ON e1.id = p.equipo_local_id
JOIN equipo e2 ON e2.id = p.equipo_visitante_id
JOIN fase f ON f.id = p.fase_id
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
ORDER BY p.numero_fifa NULLS LAST, p.id;
" > "%~dp0analisis_numeros_output.txt" 2>&1

echo.
echo Resumen - solo discrepancias:
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT
    p.id AS db_id,
    p.numero_fifa AS num_fifa,
    e1.nombre AS local,
    e2.nombre AS visitante
FROM partido p
JOIN equipo e1 ON e1.id = p.equipo_local_id
JOIN equipo e2 ON e2.id = p.equipo_visitante_id
JOIN fase f ON f.id = p.fase_id
WHERE f.torneo_id = 2
  AND f.tipo ILIKE 'grupo%%'
  AND (p.numero_fifa IS NULL OR p.id != p.numero_fifa)
ORDER BY p.numero_fifa NULLS LAST, p.id;
"

echo.
echo Resultado completo guardado en analisis_numeros_output.txt
pause
