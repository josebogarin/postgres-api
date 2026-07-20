-- migracion_monitor.sql
-- Tablas para el sistema de monitoreo de partidos en tiempo real
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_monitor.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- ── api_sync_log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_sync_log (
    id              SERIAL PRIMARY KEY,
    endpoint        TEXT,
    params          JSONB,
    status_code     INT,
    response_ms     INT,
    quota_remaining INT,
    payload_size    INT,
    error_msg       TEXT,
    origen          TEXT DEFAULT 'monitor',
    contexto        TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_sync_log_created ON api_sync_log (created_at DESC);

-- ── monitor_config ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monitor_config (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Valores por defecto
INSERT INTO monitor_config (key, value) VALUES
    ('tick_seg_lejano',    '600'),
    ('tick_seg_proximo',   '150'),
    ('tick_seg_inminente', '45'),
    ('tick_seg_ht',        '90'),
    ('max_calls_dia',      '7500')
ON CONFLICT (key) DO NOTHING;

-- ── monitor_jornada ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monitor_jornada (
    id         SERIAL PRIMARY KEY,
    fecha      DATE NOT NULL UNIQUE,
    torneo_id  INT REFERENCES torneo(id),
    estado     TEXT DEFAULT 'pendiente',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── monitor_partido_estado ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS monitor_partido_estado (
    id                SERIAL PRIMARY KEY,
    jornada_id        INT REFERENCES monitor_jornada(id),
    partido_id        INT REFERENCES partido(id),
    api_fixture_id    INT,
    estado_interno    TEXT,
    api_status_raw    TEXT,
    minuto_actual     INT,
    goles_local       INT,
    goles_visitante   INT,
    ultima_consulta   TIMESTAMPTZ,
    proxima_consulta  TIMESTAMPTZ,
    consultas_totales INT DEFAULT 0,
    intervalo_seg     INT,
    ultimo_error      TEXT,
    UNIQUE (jornada_id, partido_id)
);
