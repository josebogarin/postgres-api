-- =============================================================================
-- migracion_monitor.sql
-- Sistema de monitoreo automático de partidos — BECBUC Mundial 2026
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_monitor.sql" |
--   docker exec -i core-postgres psql -U app_user -d becbuc
-- =============================================================================

-- ---------------------------------------------------------------------------
-- monitor_jornada
-- Una fila por día que el monitor procesa.
-- estado: pendiente | activo | terminado | error | omitido
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitor_jornada (
    id                  SERIAL PRIMARY KEY,
    fecha               DATE NOT NULL,
    torneo_id           INTEGER REFERENCES torneo(id),
    estado              VARCHAR(20)  NOT NULL DEFAULT 'pendiente',
    primer_partido_utc  TIMESTAMPTZ,
    ultimo_partido_utc  TIMESTAMPTZ,
    total_partidos      SMALLINT     DEFAULT 0,
    partidos_terminales SMALLINT     DEFAULT 0,
    iniciado_en         TIMESTAMPTZ,
    terminado_en        TIMESTAMPTZ,
    ultima_actividad    TIMESTAMPTZ,
    error_msg           TEXT,
    notas               TEXT,
    created_at          TIMESTAMPTZ  DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  DEFAULT NOW(),
    CONSTRAINT uq_monitor_jornada_fecha UNIQUE (fecha)
);

-- ---------------------------------------------------------------------------
-- monitor_partido_estado
-- Estado de polling por partido. Una fila por partido. UPSERT en cada poll.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitor_partido_estado (
    id                  SERIAL PRIMARY KEY,
    partido_id          INTEGER NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
    jornada_id          INTEGER REFERENCES monitor_jornada(id),
    api_status_raw      VARCHAR(20),          -- status tal como viene de la API
    estado_interno      VARCHAR(20),          -- programado|en_juego|descanso|finalizado|suspendido
    minuto_actual       SMALLINT,
    goles_local         SMALLINT,
    goles_visitante     SMALLINT,
    es_terminal         BOOLEAN  NOT NULL DEFAULT FALSE,
    consultas_totales   INTEGER  NOT NULL DEFAULT 0,
    ultima_consulta     TIMESTAMPTZ,
    proxima_consulta    TIMESTAMPTZ,
    intervalo_seg       SMALLINT,             -- intervalo aplicado en última decisión
    ultimo_error        TEXT,
    reintentos          SMALLINT  DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_monitor_partido UNIQUE (partido_id)
);

-- ---------------------------------------------------------------------------
-- api_sync_log
-- Log de cada llamada HTTP a la API externa. Permite depurar errores de cuota.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_sync_log (
    id              BIGSERIAL PRIMARY KEY,
    endpoint        VARCHAR(300) NOT NULL,
    params          JSONB,
    status_code     SMALLINT,
    response_ms     INTEGER,
    quota_remaining INTEGER,
    error_msg       TEXT,
    payload_size    INTEGER,     -- bytes de la respuesta
    origen          VARCHAR(40), -- 'monitor' | 'sync_manual' | 'torneo_carga' etc.
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_sync_log_created  ON api_sync_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_api_sync_log_endpoint ON api_sync_log (endpoint);
CREATE INDEX IF NOT EXISTS idx_api_sync_log_error    ON api_sync_log (error_msg) WHERE error_msg IS NOT NULL;

-- ---------------------------------------------------------------------------
-- monitor_config
-- Parámetros configurables almacenados en BD (override de variables de entorno).
-- Si la clave no existe, el sistema usa el valor de .env / Settings.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitor_config (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT NOT NULL,
    tipo            VARCHAR(20) DEFAULT 'string',  -- string|int|float|bool
    descripcion     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Valores por defecto
INSERT INTO monitor_config (key, value, tipo, descripcion) VALUES
  ('interval_far_seg',      '600',  'int',   '>60 min para inicio: poll cada 10 min'),
  ('interval_near_seg',     '150',  'int',   '10–60 min para inicio: poll cada 2.5 min'),
  ('interval_imminent_seg', '45',   'int',   '<10 min para inicio: poll cada 45 s'),
  ('interval_live_seg',     '45',   'int',   'Partido en vivo: poll cada 45 s'),
  ('interval_halftime_seg', '90',   'int',   'Descanso: poll cada 90 s'),
  ('grace_period_seg',      '600',  'int',   'Espera tras todos terminales antes de cerrar jornada'),
  ('max_api_calls_dia',     '80',   'int',   'Cuota máxima de llamadas API por día'),
  ('startup_margin_seg',    '300',  'int',   'Arrancar monitor N segundos antes del primer partido'),
  ('monitor_activo',        'true', 'bool',  'Habilitar/deshabilitar el monitor global'),
  ('league_id',             '1',    'int',   'ID de liga en API-Football (1 = FIFA World Cup)'),
  ('season',                '2026', 'int',   'Temporada a monitorear')
ON CONFLICT (key) DO NOTHING;

-- Índices útiles para las consultas del monitor
CREATE INDEX IF NOT EXISTS idx_monitor_partido_terminal
    ON monitor_partido_estado (es_terminal, proxima_consulta);

CREATE INDEX IF NOT EXISTS idx_monitor_jornada_estado
    ON monitor_jornada (estado, fecha);
