-- migracion_api_log_contexto.sql
-- Agrega columna contexto a api_sync_log para mostrar estado del partido en el log del monitor
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_api_log_contexto.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE api_sync_log
    ADD COLUMN IF NOT EXISTS contexto TEXT;

-- Índice para acelerar consultas del panel de monitoreo
CREATE INDEX IF NOT EXISTS idx_api_sync_log_created ON api_sync_log (created_at DESC);
