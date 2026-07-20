-- Todos los partidos con minuto_primer_gol = 99
SELECT numero_fifa, goles_local, goles_visitante, minuto_primer_gol, estado,
       (SELECT nombre FROM equipo WHERE id=p.equipo_local_id) AS local,
       (SELECT nombre FROM equipo WHERE id=p.equipo_visitante_id) AS visitante
FROM partido p
WHERE minuto_primer_gol = 99
ORDER BY numero_fifa;
