-- reset_grupos_torneo2.sql
-- 1. Deja solo partido_id=143 (Mexico vs Sudafrica) como finalizado en grupos
-- 2. Resetea puntajes de todos los partidos de grupo excepto 143
-- 3. Limpia puntaje_detalle de esos partidos
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\reset_grupos_torneo2.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

BEGIN;

-- 1. Resetear resultados de partidos de grupo del torneo 2, excepto partido 143
UPDATE partido SET
    goles_local           = NULL,
    goles_visitante       = NULL,
    estado                = 'pendiente',
    penales_local         = NULL,
    penales_visitante     = NULL,
    amarillas             = NULL,
    rojas                 = NULL,
    decisiones_var        = NULL,
    minuto_primer_gol     = NULL,
    minuto_actual         = NULL,
    equipo_clasificado_id = NULL
WHERE torneo_id = 2
  AND id <> 143
  AND id IN (
      SELECT p.id FROM partido p
      JOIN fase f ON f.id = p.fase_id
      WHERE f.tipo = 'grupo'
  );

-- 2. Limpiar puntaje_detalle de esos partidos
DELETE FROM puntaje_detalle
WHERE partido_id <> 143
  AND partido_id IN (
      SELECT p.id FROM partido p
      JOIN fase f ON f.id = p.fase_id
      WHERE p.torneo_id = 2 AND f.tipo = 'grupo'
  );

-- 3. Reset puntos en apuesta de esos partidos
UPDATE apuesta SET puntos = 0, puntos_bonus = 0
WHERE partido_id <> 143
  AND partido_id IN (
      SELECT p.id FROM partido p
      JOIN fase f ON f.id = p.fase_id
      WHERE p.torneo_id = 2 AND f.tipo = 'grupo'
  );

-- 4. Limpiar puntaje_global (ya no es válido)
DELETE FROM puntaje_global WHERE torneo_id = 2;

-- 5. Verificación
SELECT
    COUNT(*) FILTER (WHERE estado = 'finalizado')    AS finalizados,
    COUNT(*) FILTER (WHERE estado = 'pendiente')     AS pendientes,
    COUNT(*) FILTER (WHERE goles_local IS NOT NULL)  AS con_goles
FROM partido p
JOIN fase f ON f.id = p.fase_id
WHERE p.torneo_id = 2 AND f.tipo = 'grupo';

COMMIT;
