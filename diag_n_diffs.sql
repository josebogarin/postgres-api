-- Diagnostico: partidos con N diffs para apostadores 34, 37, 42
WITH paraguay_ids AS (
    SELECT id FROM equipo WHERE UPPER(nombre) LIKE '%PARAGUAY%'
),
minuto_ganador AS (
    SELECT p.id AS partido_id,
        MIN(ABS(COALESCE(a2.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0))) AS min_diff,
        COUNT(*) FILTER (WHERE ABS(COALESCE(a2.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0)) =
            MIN(ABS(COALESCE(a2.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0))) OVER (PARTITION BY p.id)) AS n_ganadores
    FROM partido p
    JOIN apuesta a2 ON a2.partido_id = p.id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.estado = 'finalizado' AND p.minuto_primer_gol IS NOT NULL
    GROUP BY p.id
),
check_n AS (
    SELECT
        a.apostador_id,
        a.nombre_apostador,
        p.numero_fifa,
        p.minuto_primer_gol AS min_real,
        a.pred_minuto_gol AS pred_min,
        ABS(COALESCE(a.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0)) AS distancia,
        mg.min_diff,
        CASE WHEN p.minuto_primer_gol IS NOT NULL
              AND ABS(COALESCE(a.pred_minuto_gol,0) - p.minuto_primer_gol) = mg.min_diff
             THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS N_esp,
        COALESCE(pd.pts_minuto,0) AS N_bd
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
    LEFT JOIN minuto_ganador mg ON mg.partido_id = p.id
    WHERE a.apostador_id IN (34, 37, 42)
      AND f.torneo_id = 2
      AND f.tipo ILIKE 'grupo%'
      AND p.estado = 'finalizado'
      AND p.minuto_primer_gol IS NOT NULL
)
SELECT apostador_id, nombre_apostador, numero_fifa, min_real, pred_min,
       distancia, min_diff, N_esp, N_bd,
       CASE WHEN N_esp!=N_bd THEN '***DIFF' ELSE 'ok' END AS chk
FROM check_n
WHERE N_esp != N_bd
ORDER BY apostador_id, numero_fifa;
