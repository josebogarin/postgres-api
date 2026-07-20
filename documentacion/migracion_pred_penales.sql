-- migracion_pred_penales.sql
-- Sesión 2026-06-08 (parte 4)
-- Agrega predicción de penales por partido KO y columnas para scoring de bracket.
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_pred_penales.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- 1. pred_penales en apuesta: el apostador predice si el partido KO va a penales
ALTER TABLE apuesta ADD COLUMN IF NOT EXISTS pred_penales BOOLEAN DEFAULT NULL;

-- 2. Índice para acelerar la consulta de apuestas KO por apostador
CREATE INDEX IF NOT EXISTS idx_apuesta_apostador_partido
    ON apuesta (apostador_id, partido_id);

COMMENT ON COLUMN apuesta.pred_penales IS
    'Para partidos KO: TRUE = apostador predice que el partido va a penales, FALSE = no va, NULL = no apostó';
