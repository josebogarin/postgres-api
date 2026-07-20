-- ============================================================
-- limpiar_resultados_excepto_p1.sql
-- Limpia resultados del torneo Mundial 2026 EXCEPTO partido_id = 1.
-- Otros torneos NO se tocan.
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\limpiar_resultados_excepto_p1.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- 1. Ver partido_id=1 y su torneo_id
SELECT
    p.id,
    p.torneo_id,
    el.nombre           AS local,
    p.goles_local,
    p.goles_visitante,
    ev.nombre           AS visitante,
    p.estado,
    p.amarillas,
    p.rojas,
    p.decisiones_var    AS var,
    p.minuto_primer_gol AS minuto_gol,
    p.penales_local,
    p.penales_visitante,
    p.equipo_clasificado_id,
    p.api_fixture_id
FROM partido p
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.id = 1;

-- 2. Cuantos partidos del mismo torneo tienen resultado (para saber que se borra)
SELECT COUNT(*) AS partidos_con_resultado
FROM partido
WHERE id <> 1
  AND torneo_id = (SELECT torneo_id FROM partido WHERE id = 1)
  AND (goles_local IS NOT NULL OR estado = 'finalizado');

-- 3. Limpiar resultados — solo partidos del mismo torneo, excepto p.id = 1
UPDATE partido SET
    goles_local            = NULL,
    goles_visitante        = NULL,
    estado                 = 'pendiente',
    penales_local          = NULL,
    penales_visitante      = NULL,
    amarillas              = NULL,
    rojas                  = NULL,
    decisiones_var         = NULL,
    minuto_primer_gol      = NULL,
    minuto_actual          = NULL,
    equipo_clasificado_id  = NULL
WHERE id <> 1
  AND torneo_id = (SELECT torneo_id FROM partido WHERE id = 1);

-- 4. Limpiar puntaje_detalle del mismo torneo (excepto p1)
DELETE FROM puntaje_detalle
WHERE partido_id <> 1
  AND partido_id IN (
      SELECT id FROM partido
      WHERE torneo_id = (SELECT torneo_id FROM partido WHERE id = 1)
  );

-- 5. Limpiar puntaje_item del mismo torneo (si la tabla ya existe)
DO $$
DECLARE v_tid INT;
BEGIN
    SELECT torneo_id INTO v_tid FROM partido WHERE id = 1;
    IF EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'puntaje_item'
    ) THEN
        DELETE FROM puntaje_item
        WHERE torneo_id = v_tid AND categoria = 'partido' AND partido_id <> 1;
        DELETE FROM puntaje_item
        WHERE torneo_id = v_tid AND categoria = 'global';
    END IF;
END $$;

-- 6. Reset puntos en apuesta — solo partidos del mismo torneo (excepto p1)
UPDATE apuesta SET puntos = 0, puntos_bonus = 0
WHERE partido_id <> 1
  AND partido_id IN (
      SELECT id FROM partido
      WHERE torneo_id = (SELECT torneo_id FROM partido WHERE id = 1)
  );

-- 7. Limpiar puntaje global calculado del torneo
DELETE FROM puntaje_global
WHERE torneo_id = (SELECT torneo_id FROM partido WHERE id = 1);

-- 8. Resetear resultados de partidos KO del mismo torneo (sin tocar equipo_local/visitante_id)
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
WHERE id <> 1
  AND torneo_id = (SELECT torneo_id FROM partido WHERE id = 1)
  AND id IN (
      SELECT p.id FROM partido p
      JOIN fase f ON f.id = p.fase_id
      WHERE f.tipo NOT IN ('grupo')
  );

-- 9. Confirmacion final — solo del torneo afectado
SELECT
    COUNT(*) FILTER (WHERE estado = 'finalizado')   AS finalizados,
    COUNT(*) FILTER (WHERE goles_local IS NOT NULL)  AS con_goles,
    COUNT(*)                                         AS total_torneo
FROM partido
WHERE torneo_id = (SELECT torneo_id FROM partido WHERE id = 1);

COMMIT;
