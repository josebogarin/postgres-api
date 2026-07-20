-- Verificar minuto_primer_gol en partidos 0-0
SELECT numero_fifa, goles_local, goles_visitante, minuto_primer_gol, amarillas, rojas, decisiones_var, estado
FROM partido
WHERE numero_fifa IN (14, 45)
ORDER BY numero_fifa;

-- Si minuto_primer_gol es incorrecto en juegos 0-0, nulificarlo
UPDATE partido
SET minuto_primer_gol = NULL
WHERE numero_fifa IN (14, 45)
  AND goles_local = 0
  AND goles_visitante = 0
  AND minuto_primer_gol IS NOT NULL;

-- Confirmar resultado
SELECT numero_fifa, goles_local, goles_visitante, minuto_primer_gol
FROM partido
WHERE numero_fifa IN (14, 45);
