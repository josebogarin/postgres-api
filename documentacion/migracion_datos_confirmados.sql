-- Migración: datos_confirmados en partido
-- Sesión 40 — Blindaje contra sync automático
-- Idempotente: se puede ejecutar múltiples veces sin error
-- Ejecutar con:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_datos_confirmados.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE partido ADD COLUMN IF NOT EXISTS datos_confirmados BOOLEAN DEFAULT FALSE;

-- Marcar todos los partidos finalizados actuales como confirmados
-- (solo si aún no están marcados — conserva any datos_confirmados=FALSE explícito)
UPDATE partido
SET datos_confirmados = TRUE
WHERE estado = 'finalizado'
  AND (datos_confirmados IS NULL OR datos_confirmados = FALSE);

-- Verificación
SELECT
    COUNT(*) FILTER (WHERE datos_confirmados = TRUE)  AS confirmados,
    COUNT(*) FILTER (WHERE datos_confirmados = FALSE OR datos_confirmados IS NULL) AS no_confirmados,
    COUNT(*)                                           AS total
FROM partido;
