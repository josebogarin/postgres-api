-- DIAGNÓSTICO IMPORT: apuesta de CHEREM en P008 (Qatar vs Suiza)
-- Correr con:
-- docker exec -i core-postgres psql -U app_user -d becbuc < "C:\proyecto FAST API\diagnostico_import.sql"

-- 1. Qué partido es P8 en la BD (por orden)
SELECT 'PARTIDOS GRUPO (primeros 10):' as info;
SELECT
    ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq,
    p.id,
    COALESCE(el.nombre, 'TBD') AS local,
    p.goles_local,
    p.goles_visitante,
    COALESCE(ev.nombre, 'TBD') AS visitante,
    p.estado
FROM partido p
JOIN fase f ON f.id = p.fase_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.torneo_id = 2 AND f.tipo = 'grupo'
ORDER BY f.orden, p.id
LIMIT 10;

-- 2. Quién tiene apuesta en el partido #8 (grupo, posicion 8)
SELECT '--- APUESTAS P008 ---' as info;
SELECT
    ap.apostador_id,
    ap.pred_local,
    ap.pred_visitante,
    ap.puntos
FROM apuesta ap
WHERE ap.partido_id = (
    SELECT id FROM (
        SELECT p.id, ROW_NUMBER() OVER (ORDER BY f.orden, p.id) as rn
        FROM partido p JOIN fase f ON f.id = p.fase_id
        WHERE p.torneo_id = 2 AND f.tipo = 'grupo'
    ) sub WHERE rn = 8
)
ORDER BY ap.apostador_id;

-- 3. Usuarios en app_db con username parecido a 'cherem'
SELECT '--- USUARIOS EN APP_DB (buscar cherem) ---' as info;
