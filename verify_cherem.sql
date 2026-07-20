-- Verificacion completa puntaje cherem (apostador_id=15) vs calculo esperado
-- Partidos de grupos finalizados

WITH paraguay_ids AS (
    SELECT id FROM equipo WHERE UPPER(nombre) LIKE '%PARAGUAY%'
),
minuto_ganador AS (
    SELECT p.id AS partido_id,
        MIN(ABS(COALESCE(a2.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0))) AS min_diff
    FROM partido p
    JOIN apuesta a2 ON a2.partido_id = p.id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.estado = 'finalizado' AND p.minuto_primer_gol IS NOT NULL
    GROUP BY p.id
),
calc AS (
    SELECT
        p.numero_fifa,
        p.goles_local AS rl, p.goles_visitante AS rv,
        a.pred_local AS pl, a.pred_visitante AS pv,
        COALESCE(p.amarillas,0) AS amar_real, COALESCE(a.pred_amarillas,0) AS amar_pred,
        COALESCE(p.rojas,0) AS rojas_real, COALESCE(a.pred_rojas,0) AS rojas_pred,
        COALESCE(p.decisiones_var,0) AS var_real, COALESCE(a.pred_var,0) AS var_pred,
        COALESCE(p.penales_partido,0) AS pp_real, COALESCE(a.pred_penales_partido,0) AS pp_pred,
        p.minuto_primer_gol AS min_real, a.pred_minuto_gol AS pred_min,
        CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids)
              OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END AS mult,
        -- H esperado (grupos = 4 pts)
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN (a.pred_local > a.pred_visitante AND p.goles_local > p.goles_visitante)
               OR (a.pred_local = a.pred_visitante AND p.goles_local = p.goles_visitante)
               OR (a.pred_local < a.pred_visitante AND p.goles_local < p.goles_visitante)
             THEN 4 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS H_esp,
        -- I esperado (grupos = 8 pts)
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN a.pred_local = p.goles_local AND a.pred_visitante = p.goles_visitante
             THEN 8 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS I_esp,
        -- J esperado
        CASE WHEN COALESCE(a.pred_amarillas,0) = COALESCE(p.amarillas,0) THEN
             1 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS J_esp,
        -- K esperado
        CASE WHEN COALESCE(a.pred_rojas,0) = COALESCE(p.rojas,0) THEN
             1 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS K_esp,
        -- L esperado
        CASE WHEN COALESCE(a.pred_var,0) = COALESCE(p.decisiones_var,0) THEN
             1 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS L_esp,
        -- M esperado
        CASE WHEN COALESCE(a.pred_penales_partido,0) = COALESCE(p.penales_partido,0) THEN
             1 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
             ELSE 0 END AS M_esp,
        -- N esperado (1 pt si mas cercano al minuto real entre todos)
        CASE WHEN p.minuto_primer_gol IS NOT NULL
              AND ABS(COALESCE(a.pred_minuto_gol,0) - p.minuto_primer_gol) =
                  (SELECT min_diff FROM minuto_ganador mg WHERE mg.partido_id = p.id)
             THEN 1 * (CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END)
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
    WHERE a.apostador_id = 15
      AND f.torneo_id = 2
      AND f.tipo ILIKE 'grupo%'
      AND p.estado = 'finalizado'
)
SELECT
    numero_fifa, rl, rv, pl, pv, mult,
    H_esp, H_bd, CASE WHEN H_esp != H_bd THEN '***DIFF' ELSE 'ok' END AS H_chk,
    I_esp, I_bd, CASE WHEN I_esp != I_bd THEN '***DIFF' ELSE 'ok' END AS I_chk,
    J_esp, J_bd, CASE WHEN J_esp != J_bd THEN '***DIFF' ELSE 'ok' END AS J_chk,
    K_esp, K_bd, CASE WHEN K_esp != K_bd THEN '***DIFF' ELSE 'ok' END AS K_chk,
    L_esp, L_bd, CASE WHEN L_esp != L_bd THEN '***DIFF' ELSE 'ok' END AS L_chk,
    M_esp, M_bd, CASE WHEN M_esp != M_bd THEN '***DIFF' ELSE 'ok' END AS M_chk,
    N_esp, N_bd, CASE WHEN N_esp != N_bd THEN '***DIFF' ELSE 'ok' END AS N_chk
FROM calc
ORDER BY numero_fifa;

-- RESUMEN TOTALES
SELECT
    SUM(H_esp) AS H_esp_total, SUM(H_bd) AS H_bd_total,
    SUM(I_esp) AS I_esp_total, SUM(I_bd) AS I_bd_total,
    SUM(J_esp) AS J_esp_total, SUM(J_bd) AS J_bd_total,
    SUM(K_esp) AS K_esp_total, SUM(K_bd) AS K_bd_total,
    SUM(L_esp) AS L_esp_total, SUM(L_bd) AS L_bd_total,
    SUM(M_esp) AS M_esp_total, SUM(M_bd) AS M_bd_total,
    SUM(N_esp) AS N_esp_total, SUM(N_bd) AS N_bd_total,
    SUM(CASE WHEN H_esp!=H_bd THEN 1 ELSE 0 END) AS H_diffs,
    SUM(CASE WHEN I_esp!=I_bd THEN 1 ELSE 0 END) AS I_diffs,
    SUM(CASE WHEN J_esp!=J_bd THEN 1 ELSE 0 END) AS J_diffs,
    SUM(CASE WHEN K_esp!=K_bd THEN 1 ELSE 0 END) AS K_diffs,
    SUM(CASE WHEN L_esp!=L_bd THEN 1 ELSE 0 END) AS L_diffs,
    SUM(CASE WHEN M_esp!=M_bd THEN 1 ELSE 0 END) AS M_diffs,
    SUM(CASE WHEN N_esp!=N_bd THEN 1 ELSE 0 END) AS N_diffs
FROM (
    -- same CTE repeated for summary
    SELECT
        CASE WHEN p.goles_local IS NULL THEN 0 WHEN (a.pred_local>a.pred_visitante AND p.goles_local>p.goles_visitante) OR (a.pred_local=a.pred_visitante AND p.goles_local=p.goles_visitante) OR (a.pred_local<a.pred_visitante AND p.goles_local<p.goles_visitante) THEN 4*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS H_esp,
        CASE WHEN p.goles_local IS NULL THEN 0 WHEN a.pred_local=p.goles_local AND a.pred_visitante=p.goles_visitante THEN 8*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS I_esp,
        CASE WHEN COALESCE(a.pred_amarillas,0)=COALESCE(p.amarillas,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS J_esp,
        CASE WHEN COALESCE(a.pred_rojas,0)=COALESCE(p.rojas,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS K_esp,
        CASE WHEN COALESCE(a.pred_var,0)=COALESCE(p.decisiones_var,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS L_esp,
        CASE WHEN COALESCE(a.pred_penales_partido,0)=COALESCE(p.penales_partido,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS M_esp,
        CASE WHEN p.minuto_primer_gol IS NOT NULL AND ABS(COALESCE(a.pred_minuto_gol,0)-p.minuto_primer_gol)=(SELECT min_diff FROM minuto_ganador mg WHERE mg.partido_id=p.id) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END AS N_esp,
        COALESCE(pd.pts_resultado,0) AS H_bd,
        COALESCE(pd.pts_marcador,0) AS I_bd,
        COALESCE(pd.pts_amarillas,0) AS J_bd,
        COALESCE(pd.pts_rojas,0) AS K_bd,
        COALESCE(pd.pts_var,0) AS L_bd,
        COALESCE(pd.pts_penales_partido,0) AS M_bd,
        COALESCE(pd.pts_minuto,0) AS N_bd
    FROM apuesta a
    JOIN partido p ON p.id=a.partido_id
    JOIN fase f ON f.id=p.fase_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id=p.id AND pd.apostador_id=a.apostador_id
    WHERE a.apostador_id=15 AND f.torneo_id=2 AND f.tipo ILIKE 'grupo%' AND p.estado='finalizado'
) sub;
