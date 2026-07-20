-- ============================================================
-- Migración: crear base de datos becbuc y mover tablas del torneo
--
-- PASO 1 — crear la base (ejecutar como superusuario):
--   docker exec -i core-postgres psql -U app_user -d postgres -c "CREATE DATABASE becbuc OWNER app_user;"
--
-- PASO 2 — crear tablas en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_becbuc_db.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
--
-- PASO 3 — migrar datos desde app_db:
--   Get-Content "C:\proyecto FAST API\documentacion\migrar_datos_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

-- ── Tabla competicion ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS competicion (
    id              bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    api_league_id   integer UNIQUE,
    nombre          varchar(100) NOT NULL,
    nombre_corto    varchar(20),
    tipo            varchar(20)  NOT NULL DEFAULT 'copa',   -- copa | liga
    formato_playoff varchar(20)  DEFAULT 'eliminacion',
    emoji           varchar(10),
    es_activo       boolean      NOT NULL DEFAULT true
);

-- ── Tabla torneo ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS torneo (
    id              bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    competicion_id  bigint NOT NULL REFERENCES competicion(id) ON DELETE CASCADE,
    anio            integer NOT NULL,
    nombre          varchar(200),
    sede            varchar(100),
    estado          varchar(20) NOT NULL DEFAULT 'programado',
    datos_cargados  boolean NOT NULL DEFAULT false,
    api_season      integer,
    UNIQUE(competicion_id, anio)
);

-- ── Tabla equipo ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS equipo (
    id          bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    api_team_id integer UNIQUE,
    nombre      varchar(100) NOT NULL,
    nombre_es   varchar(100),
    logo_url    varchar(500),
    pais        varchar(100)
);

-- ── Tabla fase ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fase (
    id                 bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    torneo_id          bigint NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    nombre             varchar(100) NOT NULL,
    tipo               varchar(30)  NOT NULL DEFAULT 'grupo',
    orden              integer      NOT NULL DEFAULT 0,
    visible_apostador  boolean      NOT NULL DEFAULT true
);

-- ── Tabla partido ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS partido (
    id                        bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    torneo_id                 bigint NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    fase_id                   bigint NOT NULL REFERENCES fase(id) ON DELETE CASCADE,
    api_fixture_id            integer UNIQUE,
    jornada                   integer,
    fecha                     timestamptz,
    sede                      varchar(200),
    ciudad                    varchar(100),
    estado                    varchar(20) NOT NULL DEFAULT 'programado',
    equipo_local_id           bigint NOT NULL REFERENCES equipo(id),
    equipo_visitante_id       bigint NOT NULL REFERENCES equipo(id),
    goles_local               integer,
    goles_visitante           integer,
    goles_local_prorroga      integer,
    goles_visitante_prorroga  integer,
    penales_local             integer,
    penales_visitante         integer,
    leg                       varchar(10),
    partido_ida_id            bigint REFERENCES partido(id)
);

-- ── Tabla participacion (standings de grupo) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS participacion (
    id          bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    fase_id     bigint NOT NULL REFERENCES fase(id) ON DELETE CASCADE,
    equipo_id   bigint NOT NULL REFERENCES equipo(id),
    grupo       varchar(50),
    posicion    integer,
    pj          integer DEFAULT 0,
    pg          integer DEFAULT 0,
    pe          integer DEFAULT 0,
    pp          integer DEFAULT 0,
    gf          integer DEFAULT 0,
    gc          integer DEFAULT 0,
    pts         integer DEFAULT 0,
    clasifica   boolean DEFAULT false,
    UNIQUE(fase_id, equipo_id)
);

-- ── Tabla partido_estadistica ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS partido_estadistica (
    id                  bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    partido_id          bigint NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    equipo_id           bigint NOT NULL REFERENCES equipo(id),
    tiros_total         integer,
    tiros_al_arco       integer,
    posesion            numeric(5,2),
    pases_total         integer,
    pases_precision     numeric(5,2),
    faltas              integer,
    tarjetas_amarillas  integer,
    tarjetas_rojas      integer,
    fueras_de_juego     integer,
    corners             integer,
    datos_extra         jsonb,
    UNIQUE(partido_id, equipo_id)
);

-- ── Tabla partido_evento ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS partido_evento (
    id               bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    partido_id       bigint NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    equipo_id        bigint REFERENCES equipo(id),
    tipo             varchar(30),
    minuto           integer,
    minuto_extra     integer,
    jugador_nombre   varchar(100),
    asistencia_nombre varchar(100),
    detalle          varchar(100)
);

-- ── Tabla apuesta ─────────────────────────────────────────────────────────────
-- Nota: apostador_id referencia users en app_db — sin FK cross-DB, validado en app
CREATE TABLE IF NOT EXISTS apuesta (
    id              bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    apostador_id    bigint NOT NULL,          -- FK lógica a app_db.users(id)
    partido_id      bigint NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    pred_local      integer,
    pred_visitante  integer,
    pred_ganador    varchar(10) GENERATED ALWAYS AS (
        CASE
            WHEN pred_local IS NULL OR pred_visitante IS NULL THEN NULL
            WHEN pred_local  > pred_visitante THEN 'local'
            WHEN pred_local  < pred_visitante THEN 'visitante'
            ELSE 'empate'
        END
    ) STORED,
    puntos          integer,
    created_at      timestamptz DEFAULT NOW(),
    updated_at      timestamptz DEFAULT NOW(),
    UNIQUE(apostador_id, partido_id)
);

-- ── Índices ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS ix_partido_torneo  ON partido(torneo_id);
CREATE INDEX IF NOT EXISTS ix_partido_fase    ON partido(fase_id);
CREATE INDEX IF NOT EXISTS ix_participacion_fase ON participacion(fase_id);
CREATE INDEX IF NOT EXISTS ix_apuesta_apostador  ON apuesta(apostador_id);
CREATE INDEX IF NOT EXISTS ix_apuesta_partido    ON apuesta(partido_id);

-- ── Comentarios ───────────────────────────────────────────────────────────────
COMMENT ON TABLE apuesta IS 'Pronósticos de apostadores por partido';
COMMENT ON COLUMN apuesta.apostador_id IS 'ID del usuario en app_db.users (sin FK cross-DB)';
COMMENT ON COLUMN apuesta.pred_ganador IS 'Derivado automático de pred_local/pred_visitante';
COMMENT ON COLUMN apuesta.puntos IS 'Puntos otorgados tras conocer el resultado real';
