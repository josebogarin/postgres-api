-- migracion_sync_log_partido.sql
-- Agrega columnas de partido al api_sync_log para filtrado y display
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_sync_log_partido.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE api_sync_log
  ADD COLUMN IF NOT EXISTS numero_fifa  INT,
  ADD COLUMN IF NOT EXISTS fase_nm      TEXT,
  ADD COLUMN IF NOT EXISTS local_nm     TEXT,
  ADD COLUMN IF NOT EXISTS visitante_nm TEXT;

CREATE INDEX IF NOT EXISTS idx_api_sync_log_partido
  ON api_sync_log (numero_fifa, created_at DESC);

COMMENT ON COLUMN api_sync_log.numero_fifa      IS 'Número FIFA del partido (P73, P74…)';
COMMENT ON COLUMN api_sync_log.fase_nm          IS 'Nombre de la fase (Ronda 32, Cuartos…)';
COMMENT ON COLUMN api_sync_log.local_nm         IS 'Nombre equipo local';
COMMENT ON COLUMN api_sync_log.visitante_nm     IS 'Nombre equipo visitante';
