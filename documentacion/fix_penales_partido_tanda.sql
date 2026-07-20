-- Fix: penales_partido estaba sumando los kicks de la tanda de penales.
-- Para partidos KO que fueron a tanda, resetear penales_partido a NULL
-- para que el próximo sync lo recalcule correctamente.
-- Aplicar SOLO a partidos con tanda (penales_local IS NOT NULL)
-- que tienen penales_partido erróneamente alto (> 2, que sería inusual en juego normal).

-- Ver estado actual
SELECT p.numero_fifa,
       el.nombre AS local, p.goles_local, p.goles_visitante, ev.nombre AS visitante,
       p.penales_local, p.penales_visitante,
       p.penales_partido AS pp_actual,
       p.datos_confirmados
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.penales_local IS NOT NULL
ORDER BY p.numero_fifa;

-- Resetear penales_partido a NULL para que sync lo recalcule
-- (solo en partidos con tanda donde el valor parece incorrecto)
-- El admin debe ejecutar primero el SELECT y luego decidir si aplicar el UPDATE.
-- UPDATE partido
-- SET penales_partido = NULL, datos_confirmados = FALSE
-- WHERE penales_local IS NOT NULL
--   AND penales_partido > 2;  -- ajustar umbral según el caso
