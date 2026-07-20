@echo off
echo === VERIFICACION COMPLETA PUNTAJE CHEREM (apostador_id=15) === > "C:\proyecto FAST API\verify_cherem.txt"
echo === Calculo esperado (SQL) vs puntaje_detalle almacenado === >> "C:\proyecto FAST API\verify_cherem.txt"
echo. >> "C:\proyecto FAST API\verify_cherem.txt"

REM Calcular puntajes esperados vs almacenados (todos los items H,I,J,K,L,M,N por partido)
docker exec core-postgres psql -U app_user -d becbuc -c "
WITH paraguay_ids AS (
    SELECT id FROM equipo WHERE UPPER(nombre) LIKE '%%PARAGUAY%%' OR UPPER(nombre_es) LIKE '%%PARAGUAY%%'
),
fase_pts AS (
    SELECT f.id AS fase_id,
        CASE
            WHEN f.tipo ILIKE 'final' THEN 20
            WHEN f.tipo ILIKE '%%tercer%%' OR f.tipo ILIKE '%%3%%puesto%%' THEN 14
            WHEN f.tipo ILIKE '%%semi%%' THEN 12
            WHEN f.tipo ILIKE '%%cuart%%' OR f.tipo ILIKE '%%4to%%' OR f.tipo ILIKE '%%quarter%%' THEN 10
            WHEN f.tipo ILIKE '%%8vo%%' OR f.tipo ILIKE '%%octa%%' OR f.tipo ILIKE '%%round of 16%%' THEN 8
            WHEN f.tipo ILIKE '%%16%%' OR f.tipo ILIKE '%%ronda 32%%' OR f.tipo ILIKE '%%round of 32%%' THEN 6
            ELSE 4
        END AS pts_H,
        CASE
            WHEN f.tipo ILIKE 'final' THEN 40
            WHEN f.tipo ILIKE '%%tercer%%' OR f.tipo ILIKE '%%3%%puesto%%' THEN 28
            WHEN f.tipo ILIKE '%%semi%%' THEN 24
            WHEN f.tipo ILIKE '%%cuart%%' OR f.tipo ILIKE '%%4to%%' OR f.tipo ILIKE '%%quarter%%' THEN 20
            WHEN f.tipo ILIKE '%%8vo%%' OR f.tipo ILIKE '%%octa%%' OR f.tipo ILIKE '%%round of 16%%' THEN 16
            WHEN f.tipo ILIKE '%%16%%' OR f.tipo ILIKE '%%ronda 32%%' OR f.tipo ILIKE '%%round of 32%%' THEN 12
            ELSE 8
        END AS pts_I
    FROM fase f WHERE f.torneo_id = 2
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
esperado AS (
    SELECT
        p.numero_fifa,
        p.goles_local AS rl, p.goles_visitante AS rv,
        a.pred_local AS pl, a.pred_visitante AS pv,
        p.amarillas, a.pred_amarillas,
        p.rojas, a.pred_rojas,
        p.decisiones_var AS var_real, a.pred_var,
        p.penales_partido AS pp_real, a.pred_penales_partido AS pred_pp,
        p.minuto_primer_gol AS min_real, a.pred_minuto_gol AS pred_min,
        CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END AS mult,
        fp.pts_H, fp.pts_I,
        -- H: resultado
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN (a.pred_local > a.pred_visitante AND p.goles_local > p.goles_visitante)
               OR (a.pred_local = a.pred_visitante AND p.goles_local = p.goles_visitante)
               OR (a.pred_local < a.pred_visitante AND p.goles_local < p.goles_visitante)
             THEN fp.pts_H * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END
             ELSE 0 END AS H_esperado,
        -- I: marcador exacto
        CASE WHEN p.goles_local IS NULL THEN 0
             WHEN a.pred_local = p.goles_local AND a.pred_visitante = p.goles_visitante
             THEN fp.pts_I * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END
             ELSE 0 END AS I_esperado,
        -- J: amarillas
        CASE WHEN COALESCE(a.pred_amarillas,0) = COALESCE(p.amarillas,0) THEN 1 * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END ELSE 0 END AS J_esperado,
        -- K: rojas
        CASE WHEN COALESCE(a.pred_rojas,0) = COALESCE(p.rojas,0) THEN 1 * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END ELSE 0 END AS K_esperado,
        -- L: VAR
        CASE WHEN COALESCE(a.pred_var,0) = COALESCE(p.decisiones_var,0) THEN 1 * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END ELSE 0 END AS L_esperado,
        -- M: penales partido
        CASE WHEN COALESCE(a.pred_penales_partido,0) = COALESCE(p.penales_partido,0) THEN 1 * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END ELSE 0 END AS M_esperado,
        -- N: minuto (1 pt si es el mas cercano entre todos)
        CASE WHEN p.minuto_primer_gol IS NOT NULL
              AND ABS(COALESCE(a.pred_minuto_gol,0) - p.minuto_primer_gol) = (SELECT min_diff FROM minuto_ganador mg WHERE mg.partido_id = p.id)
             THEN 1 * CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END
             ELSE 0 END AS N_esperado,
        -- Almacenados en puntaje_detalle
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
    JOIN fase_pts fp ON fp.fase_id = f.id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
    WHERE a.apostador_id = 15
      AND f.torneo_id = 2
      AND f.tipo ILIKE 'grupo%%'
      AND p.estado = 'finalizado'
)
SELECT
    numero_fifa,
    rl, rv, pl, pv,
    H_esperado, H_bd, CASE WHEN H_esperado!=H_bd THEN 'DIFF' ELSE 'ok' END AS H_chk,
    I_esperado, I_bd, CASE WHEN I_esperado!=I_bd THEN 'DIFF' ELSE 'ok' END AS I_chk,
    J_esperado, J_bd, CASE WHEN J_esperado!=J_bd THEN 'DIFF' ELSE 'ok' END AS J_chk,
    K_esperado, K_bd, CASE WHEN K_esperado!=K_bd THEN 'DIFF' ELSE 'ok' END AS K_chk,
    L_esperado, L_bd, CASE WHEN L_esperado!=L_bd THEN 'DIFF' ELSE 'ok' END AS L_chk,
    M_esperado, M_bd, CASE WHEN M_esperado!=M_bd THEN 'DIFF' ELSE 'ok' END AS M_chk,
    N_esperado, N_bd, CASE WHEN N_esperado!=N_bd THEN 'DIFF' ELSE 'ok' END AS N_chk
FROM esperado
ORDER BY numero_fifa;
" >> "C:\proyecto FAST API\verify_cherem.txt" 2>&1

echo. >> "C:\proyecto FAST API\verify_cherem.txt"
echo === RESUMEN: diferencias esperado vs almacenado === >> "C:\proyecto FAST API\verify_cherem.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "
WITH paraguay_ids AS (
    SELECT id FROM equipo WHERE UPPER(nombre) LIKE '%%PARAGUAY%%' OR UPPER(nombre_es) LIKE '%%PARAGUAY%%'
),
fase_pts AS (
    SELECT f.id AS fase_id,
        CASE WHEN f.tipo ILIKE 'final' THEN 20 WHEN f.tipo ILIKE '%%semi%%' THEN 12 WHEN f.tipo ILIKE '%%cuart%%' THEN 10 WHEN f.tipo ILIKE '%%8vo%%' OR f.tipo ILIKE '%%octa%%' THEN 8 WHEN f.tipo ILIKE '%%16%%' OR f.tipo ILIKE '%%ronda 32%%' THEN 6 ELSE 4 END AS pts_H,
        CASE WHEN f.tipo ILIKE 'final' THEN 40 WHEN f.tipo ILIKE '%%semi%%' THEN 24 WHEN f.tipo ILIKE '%%cuart%%' THEN 20 WHEN f.tipo ILIKE '%%8vo%%' OR f.tipo ILIKE '%%octa%%' THEN 16 WHEN f.tipo ILIKE '%%16%%' OR f.tipo ILIKE '%%ronda 32%%' THEN 12 ELSE 8 END AS pts_I
    FROM fase f WHERE f.torneo_id = 2
),
minuto_ganador AS (
    SELECT p.id AS partido_id, MIN(ABS(COALESCE(a2.pred_minuto_gol,0) - COALESCE(p.minuto_primer_gol,0))) AS min_diff
    FROM partido p JOIN apuesta a2 ON a2.partido_id = p.id JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.estado = 'finalizado' AND p.minuto_primer_gol IS NOT NULL GROUP BY p.id
)
SELECT
    SUM(CASE WHEN (CASE WHEN p.goles_local IS NULL THEN 0 WHEN (a.pred_local>a.pred_visitante AND p.goles_local>p.goles_visitante) OR (a.pred_local=a.pred_visitante AND p.goles_local=p.goles_visitante) OR (a.pred_local<a.pred_visitante AND p.goles_local<p.goles_visitante) THEN fp.pts_H*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_resultado,0) THEN 1 ELSE 0 END) AS H_diffs,
    SUM(CASE WHEN (CASE WHEN p.goles_local IS NULL THEN 0 WHEN a.pred_local=p.goles_local AND a.pred_visitante=p.goles_visitante THEN fp.pts_I*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_marcador,0) THEN 1 ELSE 0 END) AS I_diffs,
    SUM(CASE WHEN (CASE WHEN COALESCE(a.pred_amarillas,0)=COALESCE(p.amarillas,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_amarillas,0) THEN 1 ELSE 0 END) AS J_diffs,
    SUM(CASE WHEN (CASE WHEN COALESCE(a.pred_rojas,0)=COALESCE(p.rojas,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_rojas,0) THEN 1 ELSE 0 END) AS K_diffs,
    SUM(CASE WHEN (CASE WHEN COALESCE(a.pred_var,0)=COALESCE(p.decisiones_var,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_var,0) THEN 1 ELSE 0 END) AS L_diffs,
    SUM(CASE WHEN (CASE WHEN COALESCE(a.pred_penales_partido,0)=COALESCE(p.penales_partido,0) THEN 1*(CASE WHEN p.equipo_local_id IN (SELECT id FROM paraguay_ids) OR p.equipo_visitante_id IN (SELECT id FROM paraguay_ids) THEN 2 ELSE 1 END) ELSE 0 END) != COALESCE(pd.pts_penales_partido,0) THEN 1 ELSE 0 END) AS M_diffs,
    SUM(CASE WHEN COALESCE(pd.pts_minuto,0) > 0 THEN 1 ELSE 0 END) AS N_con_puntos_bd
FROM apuesta a
JOIN partido p ON p.id=a.partido_id
JOIN fase f ON f.id=p.fase_id
JOIN fase_pts fp ON fp.fase_id=f.id
LEFT JOIN puntaje_detalle pd ON pd.partido_id=p.id AND pd.apostador_id=a.apostador_id
WHERE a.apostador_id=15 AND f.torneo_id=2 AND f.tipo ILIKE 'grupo%%' AND p.estado='finalizado';
" >> "C:\proyecto FAST API\verify_cherem.txt" 2>&1

type "C:\proyecto FAST API\verify_cherem.txt"
pause
