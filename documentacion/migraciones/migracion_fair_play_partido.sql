-- Migración: tarjetas por equipo en partido (para fair play FIFA)
-- Sesión 41 — Criterio fair play mejores terceros
-- Idempotente
-- Ejecutar con:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_fair_play_partido.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

-- Columnas por equipo en partido
ALTER TABLE partido ADD COLUMN IF NOT EXISTS local_amarillas    INT;
ALTER TABLE partido ADD COLUMN IF NOT EXISTS visitante_amarillas INT;
ALTER TABLE partido ADD COLUMN IF NOT EXISTS local_rojas        INT;
ALTER TABLE partido ADD COLUMN IF NOT EXISTS visitante_rojas    INT;

-- Columnas fair play acumulado en participacion (si no existen)
ALTER TABLE participacion ADD COLUMN IF NOT EXISTS fair_play_pts       INT DEFAULT 0;
ALTER TABLE participacion ADD COLUMN IF NOT EXISTS amarillas           INT DEFAULT 0;
ALTER TABLE participacion ADD COLUMN IF NOT EXISTS rojas_directas      INT DEFAULT 0;
ALTER TABLE participacion ADD COLUMN IF NOT EXISTS rojas_doble_amarilla INT DEFAULT 0;

-- Poblar local/visitante desde el total cuando hay ambos valores y no hay desglose aún
-- (heurística: mitad para cada equipo — se corregirá con el próximo sync)
UPDATE partido
SET
    local_amarillas     = ROUND(COALESCE(amarillas, 0) / 2.0),
    visitante_amarillas = ROUND(COALESCE(amarillas, 0) / 2.0),
    local_rojas         = ROUND(COALESCE(rojas, 0) / 2.0),
    visitante_rojas     = ROUND(COALESCE(rojas, 0) / 2.0)
WHERE estado = 'finalizado'
  AND (local_amarillas IS NULL OR visitante_amarillas IS NULL);

SELECT
    COUNT(*) FILTER (WHERE local_amarillas IS NOT NULL) AS con_desglose,
    COUNT(*) FILTER (WHERE local_amarillas IS NULL)     AS sin_desglose,
    COUNT(*)                                            AS total
FROM partido;
