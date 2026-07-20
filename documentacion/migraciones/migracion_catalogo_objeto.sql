-- ============================================================
-- Catálogo de objetos de BD (tablas y vistas) por sistema
-- Fecha: 2026-06-05
--
-- Ejecutar en app_db:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_catalogo_objeto.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

CREATE TABLE IF NOT EXISTS catalogo_objeto (
    id              SERIAL PRIMARY KEY,
    id_sistema      INTEGER NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
    nombre          VARCHAR(200) NOT NULL,           -- nombre exacto en la BD
    tipo            VARCHAR(20)  NOT NULL DEFAULT 'tabla',  -- 'tabla' | 'vista'
    alias           VARCHAR(200),                    -- nombre amigable para la UI
    descripcion     TEXT,
    solo_superadmin BOOLEAN NOT NULL DEFAULT FALSE,  -- invisible para admin/operator/viewer
    sql_definicion  TEXT,                            -- para vistas: CREATE VIEW ... (solo lectura para superadmin)
    es_activo       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (id_sistema, nombre)
);

COMMENT ON TABLE  catalogo_objeto IS 'Catálogo de tablas y vistas por sistema. Controla alias, visibilidad y acceso.';
COMMENT ON COLUMN catalogo_objeto.solo_superadmin IS 'TRUE = el objeto solo aparece para superadmin en tabla.html y diccionario.';
COMMENT ON COLUMN catalogo_objeto.sql_definicion  IS 'Definición SQL de la vista (pg_get_viewdef). Solo superadmin puede ver/editar.';

-- Índices de acceso frecuente
CREATE INDEX IF NOT EXISTS ix_catalogo_objeto_sistema ON catalogo_objeto (id_sistema);
CREATE INDEX IF NOT EXISTS ix_catalogo_objeto_tipo    ON catalogo_objeto (tipo);

-- Verificación
SELECT 'catalogo_objeto creada OK' AS estado;
