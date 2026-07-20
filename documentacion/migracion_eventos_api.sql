-- migracion_eventos_api.sql
-- Agrega columnas JSONB para eventos (goles, tarjetas) y estadísticas (posesión, tiros, etc.)
-- que se guardan en cada sync desde API-Football.
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_eventos_api.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE partido ADD COLUMN IF NOT EXISTS eventos_api      JSONB DEFAULT NULL;
ALTER TABLE partido ADD COLUMN IF NOT EXISTS estadisticas_api JSONB DEFAULT NULL;
ALTER TABLE partido ADD COLUMN IF NOT EXISTS minuto_actual    INT   DEFAULT NULL;
