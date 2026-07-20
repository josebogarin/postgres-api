-- ============================================================
-- Migración: período de apuestas por torneo
--
-- Ejecutar en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_periodo_apuestas.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

-- Período de apuestas: ventana durante la cual los apostadores pueden
-- crear/modificar sus pronósticos de fase de grupos.
-- NULL = sin restricción de tiempo (período abierto).
ALTER TABLE torneo
    ADD COLUMN IF NOT EXISTS apuesta_inicio  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS apuesta_fin     TIMESTAMPTZ;

-- Tabla de snapshots de auditoría generados por el admin
CREATE TABLE IF NOT EXISTS auditoria_apuestas (
    id            SERIAL PRIMARY KEY,
    torneo_id     INTEGER NOT NULL REFERENCES torneo(id) ON DELETE CASCADE,
    generado_por  INTEGER NOT NULL,           -- apostador_id del admin
    generado_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archivo_path  TEXT NOT NULL,              -- ruta relativa en /static/auditorias/
    descripcion   TEXT
);

-- Índice para búsqueda por torneo
CREATE INDEX IF NOT EXISTS idx_auditoria_torneo ON auditoria_apuestas(torneo_id, generado_at DESC);

-- ── Verificación ──────────────────────────────────────────────────────────────
SELECT 'torneo.apuesta_inicio'   AS columna, data_type FROM information_schema.columns WHERE table_name='torneo' AND column_name='apuesta_inicio'
UNION ALL
SELECT 'torneo.apuesta_fin',      data_type FROM information_schema.columns WHERE table_name='torneo' AND column_name='apuesta_fin'
UNION ALL
SELECT 'auditoria_apuestas (tabla)', 'exists' WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='auditoria_apuestas');
