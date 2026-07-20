-- ============================================================
-- migracion_scoring_v2.sql
-- GRUPO 0: Migracion BD para Scoring Engine v2 (BECBUC 2026)
-- Ejecutar con:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_scoring_v2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

-- 1. competicion: agregar columna codigo (identifica el engine de scoring)
ALTER TABLE competicion
    ADD COLUMN IF NOT EXISTS codigo VARCHAR(50) UNIQUE;

UPDATE competicion
SET codigo = 'copa_mundo_2026'
WHERE nombre ILIKE '%mundial%' OR nombre ILIKE '%world cup%' OR nombre ILIKE '%copa del mundo%';

-- 2. partido: agregar campos nuevos (rojas, equipo_clasificado_id)
--    NOTA: penales_partido NO se agrega (item M excluido por decision de organizacion)
ALTER TABLE partido
    ADD COLUMN IF NOT EXISTS rojas INT,
    ADD COLUMN IF NOT EXISTS equipo_clasificado_id INT REFERENCES equipo(id);

-- 3. apuesta: agregar campos nuevos para scoring v2
--    pred_penales BOOLEAN se mantiene como legacy (no borrar)
--    pred_penales_local_tanda / pred_penales_visitante_tanda reemplazan al boolean en KO
ALTER TABLE apuesta
    ADD COLUMN IF NOT EXISTS pred_rojas               INT,
    ADD COLUMN IF NOT EXISTS pred_penales_local_tanda  INT,
    ADD COLUMN IF NOT EXISTS pred_penales_visitante_tanda INT,
    ADD COLUMN IF NOT EXISTS pred_equipo_clasifica     INT;

-- 4. puntaje_detalle: agregar columnas para conceptos nuevos
ALTER TABLE puntaje_detalle
    ADD COLUMN IF NOT EXISTS pts_resultado  INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pts_rojas      INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pts_penales_tanda INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pts_equipo     INT DEFAULT 0;

-- 5. apuesta_global: pronosticos A-G por apostador x torneo
CREATE TABLE IF NOT EXISTS apuesta_global (
    id              SERIAL PRIMARY KEY,
    torneo_id       INT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    apostador_id    INT NOT NULL,
    -- A: Campeón mundial
    pred_campeon_id INT REFERENCES equipo(id),
    -- B: Finalistas (2 equipos)
    pred_finalista1_id INT REFERENCES equipo(id),
    pred_finalista2_id INT REFERENCES equipo(id),
    -- C: Goleador (texto libre, nombre del jugador)
    pred_goleador   VARCHAR(100),
    -- D: Peor equipo (el que queda último en su grupo)
    pred_peor_equipo_id INT REFERENCES equipo(id),
    -- E: Mayor goleada (marcador pronosticado: ganador y perdedor)
    pred_goleada_ganador INT,
    pred_goleada_perdedor INT,
    -- F: Etapa que alcanza Paraguay
    pred_etapa_paraguay VARCHAR(50),
    -- G: Goles totales de Paraguay en el torneo
    pred_goles_paraguay INT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (torneo_id, apostador_id)
);

-- 6. puntaje_global: resultado A-G calculados por apostador x torneo
CREATE TABLE IF NOT EXISTS puntaje_global (
    id              SERIAL PRIMARY KEY,
    torneo_id       INT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    apostador_id    INT NOT NULL,
    -- Puntos por concepto global
    pts_campeon     INT DEFAULT 0,   -- A
    pts_finalistas  INT DEFAULT 0,   -- B
    pts_goleador    INT DEFAULT 0,   -- C
    pts_peor_equipo INT DEFAULT 0,   -- D
    pts_mayor_goleada INT DEFAULT 0, -- E
    pts_etapa_paraguay INT DEFAULT 0,-- F
    pts_goles_paraguay INT DEFAULT 0,-- G
    pts_total       INT DEFAULT 0,
    calculado_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (torneo_id, apostador_id)
);

-- ============================================================
-- Verificacion post-migracion
-- ============================================================
SELECT 'competicion.codigo'       AS col, COUNT(*) AS filas FROM competicion WHERE codigo IS NOT NULL
UNION ALL
SELECT 'partido.rojas'            , COUNT(*) FROM information_schema.columns WHERE table_name='partido'           AND column_name='rojas'
UNION ALL
SELECT 'apuesta.pred_rojas'       , COUNT(*) FROM information_schema.columns WHERE table_name='apuesta'           AND column_name='pred_rojas'
UNION ALL
SELECT 'apuesta_global (tabla)'   , COUNT(*) FROM apuesta_global
UNION ALL
SELECT 'puntaje_global (tabla)'   , COUNT(*) FROM puntaje_global;
