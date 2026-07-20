-- migracion_stats_fuentes.sql
-- Tabla auxiliar para auditoría de las tres fuentes de stats por partido.
-- Almacena los valores crudos detectados por API-Football, ESPN y SofaScore,
-- y el valor final que quedó en la tabla partido.
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_stats_fuentes.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- v2: columnas de estado live/pending/finalizado agregadas en sesión 39
ALTER TABLE IF EXISTS partido_stats_fuentes
    ADD COLUMN IF NOT EXISTS estado          VARCHAR(20) DEFAULT 'pendiente',
    ADD COLUMN IF NOT EXISTS ultimo_minuto   INTEGER,
    ADD COLUMN IF NOT EXISTS fuentes_run_at  TIMESTAMPTZ;

-- v3: numero_fifa + minuto_primer_gol
ALTER TABLE IF EXISTS partido_stats_fuentes
    ADD COLUMN IF NOT EXISTS numero_fifa        VARCHAR(10),
    ADD COLUMN IF NOT EXISTS minuto_primer_gol  INTEGER;

-- v4: minuto primer gol por fuente
ALTER TABLE IF EXISTS partido_stats_fuentes
    ADD COLUMN IF NOT EXISTS api_minuto    INTEGER,
    ADD COLUMN IF NOT EXISTS espn_minuto   INTEGER,
    ADD COLUMN IF NOT EXISTS ss_minuto     INTEGER;

CREATE TABLE IF NOT EXISTS partido_stats_fuentes (
    id                  SERIAL PRIMARY KEY,
    partido_id          INTEGER NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    torneo_id           INTEGER,
    numero_fifa         VARCHAR(10),
    fecha               DATE,
    local               VARCHAR(100),
    visitante           VARCHAR(100),

    -- Fase B: API-Football (eventos directos, pre-ESPN)
    api_amarillas       INTEGER,
    api_rojas           INTEGER,
    api_var             INTEGER,
    api_penales         INTEGER,

    -- Fase C: ESPN (valores crudos detectados, independiente de lo que se aplicó)
    espn_amarillas      INTEGER,
    espn_rojas          INTEGER,
    espn_var            INTEGER,
    espn_penales        INTEGER,

    -- Fase D: SofaScore (incidents, pre-aplicación)
    ss_amarillas        INTEGER,
    ss_rojas            INTEGER,
    ss_var              INTEGER,
    ss_penales          INTEGER,

    -- Valor final aplicado en tabla partido (después de todas las fases)
    final_amarillas     INTEGER,
    final_rojas         INTEGER,
    final_var           INTEGER,
    final_penales       INTEGER,

    -- Minuto del primer gol por fuente
    api_minuto          INTEGER,
    espn_minuto         INTEGER,
    ss_minuto           INTEGER,
    minuto_primer_gol   INTEGER,   -- valor final aplicado en partido

    -- Fuente que "ganó" para cada campo (la que aportó el valor más alto)
    fuente_amarillas    VARCHAR(20),   -- 'api', 'espn', 'sofascore', 'igual'
    fuente_rojas        VARCHAR(20),
    fuente_var          VARCHAR(20),
    fuente_penales      VARCHAR(20),

    -- Estado del partido: 'pendiente' | 'live' | 'finalizado'
    estado              VARCHAR(20) DEFAULT 'pendiente',
    -- Último minuto de juego visto (para detectar cambios durante live)
    ultimo_minuto       INTEGER,
    -- Cuándo se consultaron las tres fuentes por última vez
    fuentes_run_at      TIMESTAMPTZ,

    synced_at           TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (partido_id)
);

CREATE INDEX IF NOT EXISTS idx_stats_fuentes_torneo
    ON partido_stats_fuentes (torneo_id);

CREATE INDEX IF NOT EXISTS idx_stats_fuentes_fecha
    ON partido_stats_fuentes (fecha);
