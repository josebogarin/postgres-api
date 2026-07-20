-- Verificacion global: todos los apostadores, partidos de grupos finalizados
-- Compara puntaje_detalle almacenado vs calculo esperado segun reglamento
-- Resultado: resumen de diffs por apostador

WITH paraguay_ids AS (
    SELECT id FROM equipo WHERE UPPER(nombre) LIKE '%PARAGUAY%'
),
minuto_ganador AS (
    -- Solo apostadores con pred no NULL, igual que el engine (excluye NULL = sin prediccion)
    SELECT p.id AS partido_id,
        MIN(ABS(a2.pred_minuto_gol - p.minuto_primer_gol)) AS min_diff
    FROM partido p
    JOIN apuesta a2 ON a2.partido_id = p.id AND a2.pred_minuto_gol IS NOT NULL
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.estado = 'finalizado' AND p.minuto_primer_gol IS NOT NULL
    GROUP BY p.id
),
calc AS (
    SELECT
        a.apostador_id,
        p.numero_fifa,
        CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids)
              OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END AS mult,
        -- H esperado
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN (a.pred_local>a.pred_visitante AND p.goles_local>p.goles_visitante)
               OR (a.pred_local=a.pred_visitante AND p.goles_local=p.goles_visitante)
               OR (a.pred_local<a.pred_visitante AND p.goles_local<p.goles_visitante)
             THEN 4*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS H_esp,
        -- I esperado
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN a.pred_local=p.goles_local AND a.pred_visitante=p.goles_visitante
             THEN 8*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS I_esp,
        -- J esperado
        CASE WHEN COALESCE(a.pred_amarillas,0)=COALESCE(p.amarillas,0) THEN
             1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS J_esp,
        -- K esperado
        CASE WHEN COALESCE(a.pred_rojas,0)=COALESCE(p.rojas,0) THEN
             1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS K_esp,
        -- L esperado
        CASE WHEN COALESCE(a.pred_var,0)=COALESCE(p.decisiones_var,0) THEN
             1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS L_esp,
        -- M esperado
        CASE WHEN COALESCE(a.pred_penales_partido,0)=COALESCE(p.penales_partido,0) THEN
             1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS M_esp,
        -- N esperado: solo si pred no es NULL (igual que el engine)
        CASE WHEN p.minuto_primer_gol IS NOT NULL
              AND a.pred_minuto_gol IS NOT NULL
              AND ABS(a.pred_minuto_gol - p.minuto_primer_gol) =
                  (SELECT min_diff FROM minuto_ganador mg WHERE mg.partido_id = p.id)
             THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS N_esp,
        -- Almacenados
        COALESCE(pd.pts_resultado,0) AS H_bd,
        COALESCE(pd.pts_marcador,0) AS I_bd,
        COALESCE(pd.pts_amarillas,0) AS J_bd,
        COALESCE(pd.pts_rojas,0) AS K_bd,
        COALESCE(pd.pts_var,0) AS L_bd,
        COALESCE(pd.pts_penales_partido,0) AS M_bd,
        COALESCE(pd.pts_minuto,0) AS N_bd
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
    WHERE f.torneo_id = 2
      AND f.tipo ILIKE 'grupo%'
      AND p.estado = 'finalizado'
),
diffs AS (
    SELECT
        apostador_id,
        SUM(CASE WHEN H_esp!=H_bd THEN 1 ELSE 0 END) AS H_diffs,
        SUM(CASE WHEN I_esp!=I_bd THEN 1 ELSE 0 END) AS I_diffs,
        SUM(CASE WHEN J_esp!=J_bd THEN 1 ELSE 0 END) AS J_diffs,
        SUM(CASE WHEN K_esp!=K_bd THEN 1 ELSE 0 END) AS K_diffs,
        SUM(CASE WHEN L_esp!=L_bd THEN 1 ELSE 0 END) AS L_diffs,
        SUM(CASE WHEN M_esp!=M_bd THEN 1 ELSE 0 END) AS M_diffs,
        SUM(CASE WHEN N_esp!=N_bd THEN 1 ELSE 0 END) AS N_diffs,
        SUM(CASE WHEN H_esp!=H_bd OR I_esp!=I_bd OR J_esp!=J_bd OR K_esp!=K_bd
                      OR L_esp!=L_bd OR M_esp!=M_bd OR N_esp!=N_bd THEN 1 ELSE 0 END) AS total_diffs,
        -- puntos esperados vs bd
        SUM(H_esp+I_esp+J_esp+K_esp+L_esp+M_esp+N_esp) AS pts_esp,
        SUM(H_bd+I_bd+J_bd+K_bd+L_bd+M_bd+N_bd) AS pts_bd
    FROM calc
    GROUP BY apostador_id
)
SELECT
    d.apostador_id,
    a_info.nombre_apostador AS nombre,
    d.H_diffs, d.I_diffs, d.J_diffs, d.K_diffs,
    d.L_diffs, d.M_diffs, d.N_diffs, d.total_diffs,
    d.pts_esp, d.pts_bd,
    CASE WHEN d.total_diffs = 0 THEN 'OK' ELSE '***DIFFS' END AS estado
FROM diffs d
LEFT JOIN (
    SELECT DISTINCT apostador_id, nombre_apostador
    FROM apuesta
    WHERE nombre_apostador IS NOT NULL
) a_info ON a_info.apostador_id = d.apostador_id
ORDER BY d.total_diffs DESC, d.apostador_id;
