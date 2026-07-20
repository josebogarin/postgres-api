-- ============================================================
-- MIGRACIÓN: Sistema de Torneos de Fútbol
-- Compatible con: Copa Mundial (M/F), Copa América, Eurocopa,
--                 Champions League, Copa Libertadores
-- Ejecutar en app_db
-- ============================================================

-- ── 1. Competición (catálogo fijo) ───────────────────────────
CREATE TABLE IF NOT EXISTS competicion (
    id            BIGSERIAL PRIMARY KEY,
    nombre        VARCHAR(150) NOT NULL,
    nombre_corto  VARCHAR(60),
    tipo          VARCHAR(20)  NOT NULL CHECK (tipo IN ('paises','clubes')),
    -- playoffs: partido_unico (selecciones) | ida_vuelta (clubes)
    formato_playoff VARCHAR(20) NOT NULL CHECK (formato_playoff IN ('partido_unico','ida_vuelta')),
    api_league_id INTEGER,            -- ID en API-Football
    emoji         VARCHAR(10),
    es_activo     BOOLEAN DEFAULT TRUE,
    UNIQUE(api_league_id)
);

-- ── 2. Edición / Torneo (año específico) ─────────────────────
CREATE TABLE IF NOT EXISTS torneo (
    id               BIGSERIAL PRIMARY KEY,
    competicion_id   BIGINT NOT NULL REFERENCES competicion(id),
    anio             INTEGER NOT NULL,
    nombre           VARCHAR(250),
    sede             VARCHAR(250),        -- NULL para torneos itinerantes/multi-sede
    api_season       INTEGER,             -- año de season en la API
    estado           VARCHAR(20) DEFAULT 'pendiente'
                         CHECK (estado IN ('pendiente','en_curso','finalizado')),
    datos_cargados   BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    UNIQUE(competicion_id, anio)
);

-- ── 3. Equipo ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equipo (
    id            BIGSERIAL PRIMARY KEY,
    nombre        VARCHAR(200) NOT NULL,
    nombre_corto  VARCHAR(100),
    nombre_es     VARCHAR(200),           -- nombre en español
    pais          VARCHAR(100),
    codigo_pais   VARCHAR(3),             -- ISO 3166-1 alpha-3 (ARG, BRA, ESP…)
    confederacion VARCHAR(20),            -- UEFA | CONMEBOL | CONCACAF | CAF | AFC | OFC
    tipo          VARCHAR(20) NOT NULL CHECK (tipo IN ('club','seleccion')),
    api_team_id   INTEGER UNIQUE,
    logo_url      VARCHAR(500),
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ── 4. Fase del torneo ────────────────────────────────────────
-- Ejemplos: 'Grupo A', 'Octavos de Final', 'Final'
CREATE TABLE IF NOT EXISTS fase (
    id                 BIGSERIAL PRIMARY KEY,
    torneo_id          BIGINT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    nombre             VARCHAR(100) NOT NULL,
    -- tipo: grupo | clasificatoria | playoff_prev | ronda32 | ronda16
    --       cuartos | semis | tercer_puesto | final
    tipo               VARCHAR(30)  NOT NULL,
    orden              INTEGER NOT NULL,         -- 10=grupos, 20=ronda16, 30=cuartos…
    equipos_clasifican INTEGER,                  -- cuántos avanzan por grupo (normalmente 2)
    UNIQUE(torneo_id, nombre)
);

-- ── 5. Participación (standing por fase/grupo) ────────────────
CREATE TABLE IF NOT EXISTS participacion (
    id          BIGSERIAL PRIMARY KEY,
    fase_id     BIGINT NOT NULL REFERENCES fase(id) ON DELETE CASCADE,
    equipo_id   BIGINT NOT NULL REFERENCES equipo(id),
    posicion    INTEGER,
    pj INTEGER DEFAULT 0,
    pg INTEGER DEFAULT 0,
    pe INTEGER DEFAULT 0,
    pp INTEGER DEFAULT 0,
    gf INTEGER DEFAULT 0,
    gc INTEGER DEFAULT 0,
    pts INTEGER DEFAULT 0,
    clasifica   BOOLEAN,                  -- TRUE si avanza de grupo
    UNIQUE(fase_id, equipo_id)
);

-- ── 6. Partido ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS partido (
    id                   BIGSERIAL PRIMARY KEY,
    torneo_id            BIGINT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    fase_id              BIGINT REFERENCES fase(id),
    jornada              INTEGER,         -- número de fecha/ronda
    equipo_local_id      BIGINT REFERENCES equipo(id),
    equipo_visitante_id  BIGINT REFERENCES equipo(id),
    fecha                TIMESTAMPTZ,
    sede                 VARCHAR(250),
    ciudad               VARCHAR(150),
    -- Resultado tiempo reglamentario
    goles_local          INTEGER,
    goles_visitante      INTEGER,
    -- Resultado prórroga (NULL si no hubo)
    goles_local_prorroga    INTEGER,
    goles_visitante_prorroga INTEGER,
    -- Penales (NULL si no hubo)
    penales_local        INTEGER,
    penales_visitante    INTEGER,
    -- Estado del partido
    estado VARCHAR(30) DEFAULT 'programado'
        CHECK (estado IN ('programado','en_juego','finalizado','suspendido','aplazado')),
    -- Para playoffs ida/vuelta
    leg               VARCHAR(10) CHECK (leg IN ('unico','ida','vuelta')),
    partido_ida_id    BIGINT REFERENCES partido(id),  -- FK al partido de ida
    -- Equipo que clasifica (en playoffs)
    clasificado_id    BIGINT REFERENCES equipo(id),
    -- API
    api_fixture_id    INTEGER UNIQUE,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

-- ── 7. Estadísticas de partido (por equipo) ───────────────────
CREATE TABLE IF NOT EXISTS partido_estadistica (
    id          BIGSERIAL PRIMARY KEY,
    partido_id  BIGINT NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    equipo_id   BIGINT NOT NULL REFERENCES equipo(id),
    -- Columnas estructuradas más comunes
    tiros_total       INTEGER,
    tiros_al_arco     INTEGER,
    posesion          NUMERIC(5,2),       -- porcentaje
    pases_total       INTEGER,
    pases_precision   NUMERIC(5,2),
    faltas            INTEGER,
    tarjetas_amarillas INTEGER,
    tarjetas_rojas    INTEGER,
    fueras_de_juego   INTEGER,
    corners           INTEGER,
    -- Todo lo demás en JSON flexible
    datos_extra       JSONB,
    UNIQUE(partido_id, equipo_id)
);

-- ── 8. Eventos del partido ────────────────────────────────────
CREATE TABLE IF NOT EXISTS partido_evento (
    id              BIGSERIAL PRIMARY KEY,
    partido_id      BIGINT NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    equipo_id       BIGINT REFERENCES equipo(id),
    tipo            VARCHAR(30),  -- 'gol'|'penal'|'autogol'|'amarilla'|'roja'|'sustitucion'
    minuto          INTEGER,
    minuto_extra    INTEGER,
    jugador_nombre  VARCHAR(200),
    jugador_api_id  INTEGER,
    asistencia_nombre VARCHAR(200),
    detalle         VARCHAR(100)  -- 'Normal Goal', 'Penalty', 'Own Goal', etc.
);

-- ── 9. Participación de equipo en torneo ─────────────────────
-- Registro de todos los equipos que participan en una edición
CREATE TABLE IF NOT EXISTS torneo_equipo (
    id          BIGSERIAL PRIMARY KEY,
    torneo_id   BIGINT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    equipo_id   BIGINT NOT NULL REFERENCES equipo(id),
    api_team_id INTEGER,                  -- redundancia para joins rápidos
    UNIQUE(torneo_id, equipo_id)
);

-- ── 10. Estadística por jugador (goleadores, asistencias) ─────
CREATE TABLE IF NOT EXISTS jugador_estadistica (
    id              BIGSERIAL PRIMARY KEY,
    torneo_id       BIGINT NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    equipo_id       BIGINT REFERENCES equipo(id),
    jugador_nombre  VARCHAR(200) NOT NULL,
    api_player_id   INTEGER,
    goles           INTEGER DEFAULT 0,
    asistencias     INTEGER DEFAULT 0,
    tarjetas_amarillas INTEGER DEFAULT 0,
    tarjetas_rojas  INTEGER DEFAULT 0,
    partidos_jugados INTEGER DEFAULT 0,
    UNIQUE(torneo_id, api_player_id)
);

-- ── ÍNDICES ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_torneo_competicion ON torneo(competicion_id);
CREATE INDEX IF NOT EXISTS idx_fase_torneo        ON fase(torneo_id);
CREATE INDEX IF NOT EXISTS idx_partido_torneo     ON partido(torneo_id);
CREATE INDEX IF NOT EXISTS idx_partido_fase       ON partido(fase_id);
CREATE INDEX IF NOT EXISTS idx_partido_api        ON partido(api_fixture_id);
CREATE INDEX IF NOT EXISTS idx_equipo_api         ON equipo(api_team_id);
CREATE INDEX IF NOT EXISTS idx_torneo_equipo      ON torneo_equipo(torneo_id);
CREATE INDEX IF NOT EXISTS idx_jugador_torneo     ON jugador_estadistica(torneo_id);
CREATE INDEX IF NOT EXISTS idx_evento_partido     ON partido_evento(partido_id);

-- ── SEED: Competiciones soportadas ───────────────────────────
INSERT INTO competicion (nombre, nombre_corto, tipo, formato_playoff, api_league_id, emoji)
VALUES
  ('Copa Mundial FIFA (Masculino)',  'Mundial Masc.',  'paises',  'partido_unico', 1,  '🌍'),
  ('Copa Mundial FIFA (Femenino)',   'Mundial Fem.',   'paises',  'partido_unico', 6,  '🌍'),
  ('Copa América',                   'Copa América',   'paises',  'partido_unico', 9,  '🏆'),
  ('UEFA Eurocopa',                  'Eurocopa',       'paises',  'partido_unico', 4,  '🏆'),
  ('UEFA Champions League',          'Champions',      'clubes',  'ida_vuelta',    2,  '⭐'),
  ('Copa Libertadores',              'Libertadores',   'clubes',  'ida_vuelta',    13, '🦅')
ON CONFLICT (api_league_id) DO NOTHING;
