-- ============================================================
-- fix_partido_id_apuestas.sql
-- Corrige apuesta.partido_id que fue asignado por num_seq
-- (ROW_NUMBER por orden BD) en vez de numero_fifa (orden FIFA).
--
-- EJECUTAR:
--   Get-Content "C:\proyecto FAST API\documentacion\fix_partido_id_apuestas.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- ── 1. Diagnóstico: ver discrepancias num_seq vs numero_fifa ──────────────────
-- (descomentar para revisar antes de aplicar)
/*
WITH ranked AS (
    SELECT
        p.id          AS partido_id,
        p.numero_fifa AS numero_fifa,
        ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq,
        COALESCE(el.nombre_es, el.nombre) AS local,
        COALESCE(ev.nombre_es, ev.nombre) AS visitante
    FROM partido p
    JOIN fase    f  ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id = 2 AND f.tipo = 'grupo'
    ORDER BY f.orden, p.id
)
SELECT num_seq, numero_fifa,
       CASE WHEN num_seq = numero_fifa THEN 'OK' ELSE '*** DIFF ***' END AS estado,
       local, visitante
FROM ranked
ORDER BY num_seq;
*/

-- ── 2. Tabla temporal con el mapeo de corrección ──────────────────────────────
-- old_partido_id = el partido que quedó asignado por num_seq
-- new_partido_id = el partido correcto según numero_fifa
CREATE TEMP TABLE _correccion AS
WITH ranked AS (
    SELECT
        p.id          AS partido_id,
        p.numero_fifa AS numero_fifa,
        ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND f.tipo = 'grupo'
    ORDER BY f.orden, p.id
),
old_map AS (
    SELECT num_seq, partido_id AS old_partido_id FROM ranked
),
new_map AS (
    SELECT numero_fifa AS fifa_num, partido_id AS new_partido_id
    FROM ranked
    WHERE numero_fifa IS NOT NULL AND numero_fifa > 0
)
SELECT
    o.num_seq,
    o.old_partido_id,
    n.new_partido_id
FROM old_map  o
JOIN new_map  n ON o.num_seq = n.fifa_num
WHERE o.old_partido_id <> n.new_partido_id;   -- solo donde hay diferencia

-- Ver cuántos partidos difieren
SELECT COUNT(*) AS partidos_con_discrepancia FROM _correccion;

-- ── 3. Corregir apuesta.partido_id ───────────────────────────────────────────
-- Cuenta afectados antes
SELECT COUNT(*) AS apuestas_a_corregir
FROM apuesta a
JOIN _correccion c ON a.partido_id = c.old_partido_id;

UPDATE apuesta
SET partido_id = c.new_partido_id
FROM _correccion c
WHERE apuesta.partido_id = c.old_partido_id;

-- ── 4. Corregir puntaje_detalle.partido_id (si existe) ───────────────────────
UPDATE puntaje_detalle
SET partido_id = c.new_partido_id
FROM _correccion c
WHERE puntaje_detalle.partido_id = c.old_partido_id;

-- ── 5. Resultado ──────────────────────────────────────────────────────────────
SELECT
    c.num_seq,
    c.old_partido_id,
    c.new_partido_id,
    COALESCE(el.nombre_es, el.nombre) AS local_correcto,
    COALESCE(ev.nombre_es, ev.nombre) AS visitante_correcto
FROM _correccion c
JOIN partido p  ON p.id  = c.new_partido_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
ORDER BY c.num_seq;

COMMIT;

-- Después de ejecutar:
-- POST /api/v1/bets/calcular-puntajes/2  (recalcular con los partido_id corregidos)
