-- Fix pred_rojas de Quiroga: poner 0 en todos los partidos
-- excepto España vs Cabo Verde (que se deja como está)
UPDATE apuesta a
SET pred_rojas = 0
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE a.partido_id = p.id
  AND a.nombre_apostador ILIKE '%quiroga%'
  AND NOT (
      (el.nombre ILIKE '%spain%' OR el.nombre_es ILIKE '%espa%')
      AND
      (ev.nombre ILIKE '%cape verde%' OR ev.nombre_es ILIKE '%cabo verde%')
  );

-- Verificar resultado
SELECT p.id,
       COALESCE(el.nombre_es, el.nombre) AS local,
       COALESCE(ev.nombre_es, ev.nombre) AS visitante,
       a.pred_rojas
FROM apuesta a
JOIN partido p  ON p.id = a.partido_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE a.nombre_apostador ILIKE '%quiroga%'
  AND p.estado = 'finalizado'
ORDER BY p.id;
