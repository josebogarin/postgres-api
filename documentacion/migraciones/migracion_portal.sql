-- ============================================================
-- Portal: tablas de configuración (KPIs y vínculos)
-- Ejecutar en app_db como app_user o superuser
-- ============================================================

CREATE TABLE IF NOT EXISTS portal_kpis (
    id          BIGSERIAL PRIMARY KEY,
    id_sistema  BIGINT REFERENCES sistema(id) ON DELETE CASCADE,
    titulo      VARCHAR(100)  NOT NULL,
    icono       VARCHAR(50)   NOT NULL DEFAULT 'ti-chart-bar',
    color       VARCHAR(20)   NOT NULL DEFAULT 'teal',
    query_sql   TEXT          NOT NULL,
    formato     VARCHAR(20)   NOT NULL DEFAULT 'number',  -- number | currency | percent
    decimales   INTEGER       DEFAULT 0,
    prefijo     VARCHAR(10)   DEFAULT '',
    sufijo      VARCHAR(10)   DEFAULT '',
    orden       INTEGER       DEFAULT 0,
    es_activo   BOOLEAN       DEFAULT true,
    created_at  TIMESTAMP     DEFAULT NOW(),
    updated_at  TIMESTAMP     DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portal_vinculos (
    id          BIGSERIAL PRIMARY KEY,
    id_sistema  BIGINT REFERENCES sistema(id) ON DELETE CASCADE,
    titulo      VARCHAR(100)  NOT NULL,
    url         TEXT          NOT NULL,
    icono       VARCHAR(50)   NOT NULL DEFAULT 'ti-external-link',
    descripcion TEXT,
    orden       INTEGER       DEFAULT 0,
    es_activo   BOOLEAN       DEFAULT true,
    created_at  TIMESTAMP     DEFAULT NOW(),
    updated_at  TIMESTAMP     DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_portal_kpis_sistema    ON portal_kpis(id_sistema);
CREATE INDEX IF NOT EXISTS idx_portal_vinculos_sistema ON portal_vinculos(id_sistema);
