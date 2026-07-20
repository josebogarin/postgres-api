-- migracion_equipo_competicion.sql
-- Agrega competicion_id a equipo para aislar equipos por competicion.
-- Impide mezcla de clubes con selecciones nacionales.
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_equipo_competicion.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- ── 1. Agregar columna competicion_id a equipo ────────────────────────────────
ALTER TABLE equipo
    ADD COLUMN IF NOT EXISTS competicion_id INT REFERENCES competicion(id);

-- ── 2. Agregar columna numero_equipos esperado a competicion ──────────────────
--    Copa del Mundo 2026: 48 equipos
--    Libertadores:        32 equipos (fase grupos)
--    Otros: NULL = sin validacion
ALTER TABLE competicion
    ADD COLUMN IF NOT EXISTS num_equipos_esperado INT;

-- ── 3. Poblar num_equipos_esperado para competiciones conocidas ───────────────
UPDATE competicion
   SET num_equipos_esperado = 48
 WHERE codigo = 'copa_mundo_2026';

-- ── 4. Asignar competicion_id a equipos existentes segun participacion ────────
--    Los equipos que esten en participacion de un torneo heredan la competicion
--    de ese torneo (primera ocurrencia si aparecen en varias).
UPDATE equipo e
   SET competicion_id = sub.competicion_id
  FROM (
      SELECT DISTINCT ON (par.equipo_id)
             par.equipo_id,
             t.competicion_id
        FROM participacion par
        JOIN fase f   ON f.id  = par.fase_id
        JOIN torneo t ON t.id  = f.torneo_id
       WHERE t.competicion_id IS NOT NULL
       ORDER BY par.equipo_id, t.id
  ) sub
 WHERE e.id = sub.equipo_id
   AND e.competicion_id IS NULL;

-- ── 5. Vista de verificacion rapida ──────────────────────────────────────────
CREATE OR REPLACE VIEW v_equipos_por_competicion AS
SELECT
    c.id          AS competicion_id,
    c.nombre      AS competicion,
    c.codigo,
    c.num_equipos_esperado,
    COUNT(e.id)   AS total_equipos,
    CASE
        WHEN c.num_equipos_esperado IS NULL THEN 'sin_validacion'
        WHEN COUNT(e.id) = c.num_equipos_esperado THEN 'OK'
        WHEN COUNT(e.id) < c.num_equipos_esperado THEN 'FALTAN_EQUIPOS'
        ELSE 'EQUIPOS_DE_MAS'
    END           AS estado_count,
    COUNT(e.id) FILTER (WHERE e.codigo_iso IS NOT NULL) AS con_iso,
    COUNT(e.id) FILTER (WHERE e.fifa_ranking IS NOT NULL) AS con_ranking
FROM competicion c
LEFT JOIN equipo e ON e.competicion_id = c.id
GROUP BY c.id, c.nombre, c.codigo, c.num_equipos_esperado
ORDER BY c.id;

-- ── 6. Vista de partidos con equipos de competicion incorrecta ────────────────
CREATE OR REPLACE VIEW v_partidos_equipos_cross AS
SELECT
    p.id          AS partido_id,
    t.id          AS torneo_id,
    t.nombre      AS torneo,
    c.codigo      AS competicion_codigo,
    el.nombre     AS local,
    el.competicion_id AS local_comp_id,
    ev.nombre     AS visitante,
    ev.competicion_id AS visit_comp_id,
    CASE
        WHEN el.competicion_id IS DISTINCT FROM t.competicion_id THEN 'LOCAL_WRONG'
        WHEN ev.competicion_id IS DISTINCT FROM t.competicion_id THEN 'VISIT_WRONG'
        ELSE 'OK'
    END           AS estado
FROM partido p
JOIN fase f   ON f.id  = p.fase_id
JOIN torneo t ON t.id  = f.torneo_id
JOIN competicion c ON c.id = t.competicion_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE el.competicion_id IS DISTINCT FROM t.competicion_id
   OR ev.competicion_id IS DISTINCT FROM t.competicion_id;

-- Verificacion post-migracion:
-- SELECT * FROM v_equipos_por_competicion;
-- SELECT COUNT(*) FROM v_partidos_equipos_cross;
