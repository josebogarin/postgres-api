-- fix_pts_equipo_grupos.sql
-- Elimina el doble-conteo del ítem P en partidos de fase de grupos.
-- El engine tenía pts_equipo_clasifica=1 para grupos, pero el P de grupos
-- se calcula correctamente en apostador_clasificados (max 32 pts, 1pt x equipo clasificado a R32).
-- Los partidos de grupo tienen equipo_clasificado_id = ganador del partido, por lo que
-- el engine les asignaba pts_equipo incorrectamente.
-- Tras este fix: pts_equipo=0 para TODOS los partidos de grupos, ajustando pts_bonus y pts_total.

UPDATE puntaje_detalle pd
SET
    pts_total  = pts_total  - COALESCE(pts_equipo, 0),
    pts_bonus  = pts_bonus  - COALESCE(pts_equipo, 0),
    pts_equipo = 0
WHERE COALESCE(pts_equipo, 0) > 0
  AND pd.partido_id IN (
      SELECT p.id
      FROM partido p
      JOIN fase f ON f.id = p.fase_id
      WHERE LOWER(f.tipo) LIKE '%grupo%'
  );
