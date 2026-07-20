-- ============================================================
-- Mensajes del administrador a los apostadores
-- Ejecutar en becbuc:
-- Get-Content "C:\proyecto FAST API\documentacion\migracion_mensajes_admin.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

CREATE TABLE IF NOT EXISTS mensaje_admin (
    id           BIGSERIAL PRIMARY KEY,
    numero       SMALLINT    NOT NULL DEFAULT 1,     -- secuencial por torneo
    torneo_id    BIGINT      REFERENCES torneo(id) ON DELETE CASCADE,
    titulo       VARCHAR(200) NOT NULL,
    contenido    TEXT        NOT NULL,
    autor_id     INTEGER     NOT NULL,               -- id del usuario en app_db
    autor_nombre VARCHAR(200),                       -- nombre cacheado
    es_activo    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mensaje_admin_torneo
    ON mensaje_admin(torneo_id, created_at DESC);

COMMENT ON TABLE mensaje_admin IS 'Mensajes del administrador visibles para todos los apostadores del torneo.';
COMMENT ON COLUMN mensaje_admin.numero IS 'Numero secuencial por torneo (1, 2, 3...).';
