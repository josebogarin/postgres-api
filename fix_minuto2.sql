-- Fix minuto_primer_gol erroneo en juegos 0-0
-- P34, P39, P60 (igual que P14/P45 ya corregidos)
SELECT numero_fifa, goles_local, goles_visitante, minuto_primer_gol, estado
FROM partido WHERE numero_fifa IN (34, 39, 60) ORDER BY numero_fifa;

UPDATE partido
SET minuto_primer_gol = NULL
WHERE numero_fifa IN (34, 39, 60)
  AND goles_local = 0 AND goles_visitante = 0
  AND minuto_primer_gol IS NOT NULL;

SELECT numero_fifa, goles_local, goles_visitante, minuto_primer_gol
FROM partido WHERE numero_fifa IN (34, 39, 60) ORDER BY numero_fifa;
