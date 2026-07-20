-- fix_tarjetas_r32.sql
-- Recalcula amarillas y rojas para partidos R32 finalizados
-- desde eventos_api guardados en BD, aplicando las reglas correctas:
--   - Excluir tarjetas al banco/staff (player.id = null)
--   - "Second Yellow card" cuenta como roja (no como amarilla)
--   - "Yellow Card" solo cuenta si player.id no es null
-- REGLA: NULL = 0 para resultados de tarjetas en partidos finalizados

UPDATE partido p
SET
  amarillas = sub.n_amar,
  rojas     = sub.n_rojas
FROM (
  SELECT
    p2.id AS pid,
    COUNT(*) FILTER (
      WHERE ev->>'type' = 'Card'
        AND ev->>'detail' = 'Yellow Card'
        AND (ev->'player'->>'id') IS NOT NULL
    ) AS n_amar,
    COUNT(*) FILTER (
      WHERE ev->>'type' = 'Card'
        AND ev->>'detail' IN ('Red Card', 'Second Yellow card')
        AND (ev->'player'->>'id') IS NOT NULL
    ) AS n_rojas
  FROM partido p2
  JOIN fase f ON f.id = p2.fase_id
  CROSS JOIN LATERAL jsonb_array_elements(p2.eventos_api) AS ev
  WHERE f.torneo_id = 2
    AND f.tipo = 'ronda32'
    AND p2.estado = 'finalizado'
    AND p2.eventos_api IS NOT NULL
    AND jsonb_array_length(p2.eventos_api) > 0
  GROUP BY p2.id
) sub
WHERE p.id = sub.pid
  AND (p.amarillas IS DISTINCT FROM sub.n_amar
    OR p.rojas     IS DISTINCT FROM sub.n_rojas);

-- Paso 2: NULL → 0 para partidos finalizados sin eventos_api (ej: P73)
UPDATE partido p
SET
  amarillas = COALESCE(p.amarillas, 0),
  rojas     = COALESCE(p.rojas, 0)
FROM fase f
WHERE f.id = p.fase_id
  AND f.torneo_id = 2
  AND f.tipo = 'ronda32'
  AND p.estado = 'finalizado'
  AND (p.amarillas IS NULL OR p.rojas IS NULL);

-- Ver qué cambió
SELECT p.numero_fifa,
       el.nombre AS local, p.goles_local, p.goles_visitante, ev.nombre AS visitante,
       p.amarillas, p.rojas, p.estado
FROM partido p
JOIN equipo el ON p.equipo_local_id = el.id
JOIN equipo ev ON p.equipo_visitante_id = ev.id
JOIN fase f ON f.id = p.fase_id
WHERE f.torneo_id = 2 AND f.tipo = 'ronda32'
ORDER BY p.numero_fifa;
