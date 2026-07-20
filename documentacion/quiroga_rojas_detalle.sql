SELECT
    p.id                                        AS partido_id,
    COALESCE(el.nombre_es, el.nombre)           AS local,
    p.goles_local,
    p.goles_visitante,
    COALESCE(ev.nombre_es, ev.nombre)           AS visitante,
    COALESCE(p.rojas, 0)                        AS real_rojas,
    COALESCE(a.pred_rojas, 0)                   AS pred_rojas,
    COALESCE(d.pts_rojas, 0)                    AS pts_k
FROM apuesta a
JOIN partido p  ON p.id  = a.partido_id
JOIN fase   f  ON f.id  = p.fase_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
LEFT JOIN puntaje_detalle d
       ON d.partido_id   = a.partido_id
      AND d.apostador_id = a.apostador_id
WHERE a.nombre_apostador ILIKE '%quiroga%'
  AND p.estado = 'finalizado'
ORDER BY p.id;
