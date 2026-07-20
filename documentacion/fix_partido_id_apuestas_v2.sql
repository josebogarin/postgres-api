-- ============================================================
-- fix_partido_id_apuestas_v2.sql
-- Corrige apuesta.partido_id (num_seq → numero_fifa) manejando
-- duplicados: si la apuesta correcta ya existe, borra la errónea.
-- También agrega columna numero_fifa a apuesta y la puebla.
--
-- EJECUTAR:
--   Get-Content "C:\proyecto FAST API\documentacion\fix_partido_id_apuestas_v2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- ── 0. Agregar numero_fifa a apuesta (idempotente) ───────────────────────────
ALTER TABLE apuesta ADD COLUMN IF NOT EXISTS numero_fifa INT DEFAULT NULL;

-- ── 1. Tabla de corrección: old_partido_id → new_partido_id ──────────────────
CREATE TEMP TABLE _correccion AS
WITH ranked AS (
    SELECT
        p.id          AS partido_id,
        p.numero_fifa AS numero_fifa,
        ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND f.tipo = 'grupo'
),
old_map AS (SELECT num_seq, partido_id AS old_pid FROM ranked),
new_map AS (SELECT numero_fifa AS num, partido_id AS new_pid FROM ranked WHERE numero_fifa > 0)
SELECT o.num_seq, o.old_pid, n.new_pid, n.num AS numero_fifa_val
FROM old_map o
JOIN new_map n ON o.num_seq = n.num
WHERE o.old_pid <> n.new_pid;

SELECT COUNT(*) AS partidos_con_discrepancia FROM _correccion;

-- ── 2. Clasificar cada apuesta errónea ───────────────────────────────────────
-- "tiene_correcta" = ya existe una apuesta del mismo apostador para new_pid
CREATE TEMP TABLE _afix AS
SELECT
    a.id              AS apuesta_id,
    a.apostador_id,
    c.old_pid,
    c.new_pid,
    c.numero_fifa_val,
    EXISTS (
        SELECT 1 FROM apuesta a2
        WHERE a2.apostador_id = a.apostador_id
          AND a2.partido_id   = c.new_pid
    ) AS tiene_correcta
FROM apuesta a
JOIN _correccion c ON a.partido_id = c.old_pid;

SELECT
    SUM(CASE WHEN NOT tiene_correcta THEN 1 ELSE 0 END) AS a_actualizar,
    SUM(CASE WHEN     tiene_correcta THEN 1 ELSE 0 END) AS a_borrar_duplicada
FROM _afix;

-- ── 3a. UPDATE: mover partido_id al correcto (donde no hay duplicado) ─────────
UPDATE apuesta
SET
    partido_id  = f.new_pid,
    numero_fifa = f.numero_fifa_val
FROM _afix f
WHERE apuesta.id = f.apuesta_id
  AND NOT f.tiene_correcta;

-- ── 3b. DELETE: borrar la apuesta errónea si la correcta ya existe ────────────
DELETE FROM puntaje_detalle
WHERE (apostador_id, partido_id) IN (
    SELECT apostador_id, old_pid FROM _afix WHERE tiene_correcta
);

DELETE FROM apuesta
WHERE id IN (SELECT apuesta_id FROM _afix WHERE tiene_correcta);

-- ── 4. Poblar numero_fifa en apuestas ya correctas (que no pasaron por fix) ──
UPDATE apuesta a
SET numero_fifa = p.numero_fifa
FROM partido p
WHERE a.partido_id = p.id
  AND a.numero_fifa IS NULL
  AND p.numero_fifa IS NOT NULL;

-- ── 5. Corregir puntaje_detalle.partido_id (para los que se actualizaron) ─────
UPDATE puntaje_detalle pd
SET partido_id = f.new_pid
FROM _afix f
WHERE pd.partido_id   = f.old_pid
  AND pd.apostador_id = f.apostador_id
  AND NOT f.tiene_correcta;

-- ── 6. Resumen final ──────────────────────────────────────────────────────────
SELECT
    COUNT(*)                                    AS total_apuestas,
    COUNT(numero_fifa)                          AS con_numero_fifa,
    COUNT(*) - COUNT(numero_fifa)               AS sin_numero_fifa
FROM apuesta
WHERE partido_id IN (
    SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=2 AND f.tipo='grupo'
);

COMMIT;

-- Paso siguiente obligatorio: recalcular puntajes con partido_ids corregidos
-- POST /api/v1/bets/calcular-puntajes/2
