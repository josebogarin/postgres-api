-- ============================================================
-- Migración: columnas para criterios de desempate FIFA 2026
--
-- Ejecutar en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_tiebreakers_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

-- ── 1. equipo: ranking FIFA (menor número = mejor posición) ──────────────────
ALTER TABLE equipo
    ADD COLUMN IF NOT EXISTS fifa_ranking INTEGER;

-- ── 2. participacion: disciplina acumulada en el grupo ───────────────────────
-- amarillas: total tarjetas amarillas del equipo en la fase
-- rojas_directas: expulsiones directas (roja sin previa amarilla)
-- rojas_doble_amarilla: expulsiones por segunda amarilla
-- fair_play_pts: calculado como amarillas*(-1) + rojas_directas*(-3) + rojas_doble_amarilla*(-3)
-- (valor negativo → peor; 0 → sin tarjetas → mejor)
ALTER TABLE participacion
    ADD COLUMN IF NOT EXISTS amarillas          INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS rojas_directas     INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS rojas_doble_amarilla INTEGER NOT NULL DEFAULT 0;

-- fair_play_pts es calculado; se guarda para eficiencia de queries
ALTER TABLE participacion
    ADD COLUMN IF NOT EXISTS fair_play_pts INTEGER
        GENERATED ALWAYS AS (
            amarillas * (-1)
            + rojas_directas * (-3)
            + rojas_doble_amarilla * (-3)
        ) STORED;

-- ── 3. partido_estadistica: distinguir tipo de roja ──────────────────────────
-- La tabla ya tiene tarjetas_rojas (total). Agregamos desglose.
ALTER TABLE partido_estadistica
    ADD COLUMN IF NOT EXISTS tarjetas_rojas_directas    INTEGER,
    ADD COLUMN IF NOT EXISTS tarjetas_rojas_doble_amari  INTEGER;

-- ── Verificación ─────────────────────────────────────────────────────────────
SELECT 'equipo.fifa_ranking'               AS columna, data_type FROM information_schema.columns WHERE table_name='equipo'           AND column_name='fifa_ranking'
UNION ALL
SELECT 'participacion.amarillas',            data_type FROM information_schema.columns WHERE table_name='participacion'    AND column_name='amarillas'
UNION ALL
SELECT 'participacion.rojas_directas',       data_type FROM information_schema.columns WHERE table_name='participacion'    AND column_name='rojas_directas'
UNION ALL
SELECT 'participacion.rojas_doble_amarilla', data_type FROM information_schema.columns WHERE table_name='participacion'    AND column_name='rojas_doble_amarilla'
UNION ALL
SELECT 'participacion.fair_play_pts',        data_type FROM information_schema.columns WHERE table_name='participacion'    AND column_name='fair_play_pts'
UNION ALL
SELECT 'partido_estadistica.rojas_directas', data_type FROM information_schema.columns WHERE table_name='partido_estadistica' AND column_name='tarjetas_rojas_directas';
