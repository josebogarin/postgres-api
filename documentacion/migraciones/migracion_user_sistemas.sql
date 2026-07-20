-- ============================================================
-- Migración: tabla user_sistemas
-- Asocia usuarios con los sistemas a los que tienen acceso.
-- Superadmin accede a todos sin restricción.
-- ============================================================

CREATE TABLE IF NOT EXISTS user_sistemas (
    user_id    BIGINT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    sistema_id BIGINT NOT NULL REFERENCES sistema(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL,
    PRIMARY KEY (user_id, sistema_id)
);

CREATE INDEX IF NOT EXISTS ix_user_sistemas_user_id    ON user_sistemas (user_id);
CREATE INDEX IF NOT EXISTS ix_user_sistemas_sistema_id ON user_sistemas (sistema_id);
