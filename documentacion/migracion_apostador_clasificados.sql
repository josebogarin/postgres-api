-- ============================================================
-- migracion_apostador_clasificados.sql
-- Item P (equipo clasifica) por fase — auditoría y scoring grupos
-- ============================================================

-- Tabla principal: una fila por apostador × torneo × fase
CREATE TABLE IF NOT EXISTS apostador_clasificados (
    id                     SERIAL PRIMARY KEY,
    torneo_id              INTEGER NOT NULL,
    apostador_id           INTEGER NOT NULL,
    fase_tipo              VARCHAR(50) NOT NULL,   -- 'grupo', 'ronda32', 'ronda16', 'cuartos', 'semis', 'tercer_puesto', 'final'
    -- Arrays con IDs de equipos (INTEGER[])
    equipos_pronosticados  INTEGER[] DEFAULT '{}', -- IDs de equipos predichos como clasificados a la sig. fase
    equipos_reales         INTEGER[] DEFAULT '{}', -- IDs de equipos que realmente clasificaron
    aciertos               INTEGER DEFAULT 0,
    pts_por_acierto        INTEGER DEFAULT 1,      -- pts base segun reglamento: 1/2/4/6/8/10/12
    pts_obtenidos          INTEGER DEFAULT 0,      -- aciertos × pts_por_acierto
    calculado_at           TIMESTAMP DEFAULT NOW(),
    UNIQUE(torneo_id, apostador_id, fase_tipo)
);

CREATE INDEX IF NOT EXISTS idx_apclas_torneo_ap
    ON apostador_clasificados(torneo_id, apostador_id);

CREATE INDEX IF NOT EXISTS idx_apclas_torneo_fase
    ON apostador_clasificados(torneo_id, fase_tipo);

-- ============================================================
-- EJECUTAR:
-- Get-Content "C:\proyecto FAST API\documentacion\migracion_apostador_clasificados.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================
