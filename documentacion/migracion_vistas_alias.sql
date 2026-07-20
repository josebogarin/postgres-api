-- Migración: actualizar vistas para usar username (alias) desde app_db via dblink
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migracion_vistas_alias.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

CREATE EXTENSION IF NOT EXISTS dblink;

-- ============================================================
-- Vista v_copamundial_puntajes (resumen por apostador)
-- ============================================================
DROP VIEW IF EXISTS v_copamundial_puntajes;

CREATE VIEW v_copamundial_puntajes AS
WITH usernames AS (
    SELECT u.id::int AS apostador_id, u.username
    FROM dblink(
        'host=localhost port=5432 dbname=app_db user=app_user password=superpassword',
        'SELECT id, username FROM users WHERE username IS NOT NULL'
    ) AS u(id bigint, username text)
),
nombres AS (
    SELECT DISTINCT ON (apostador_id)
        apostador_id,
        nombre_apostador AS nombre
    FROM apuesta
    WHERE nombre_apostador IS NOT NULL
    ORDER BY apostador_id, updated_at DESC NULLS LAST
),
items_partido AS (
    SELECT
        d.apostador_id,
        COUNT(DISTINCT CASE WHEN p.estado = 'finalizado' THEN d.partido_id END) AS partidos_finalizados,
        COALESCE(SUM(d.pts_resultado),       0) AS pts_H,
        COALESCE(SUM(d.pts_marcador),        0) AS pts_I,
        COALESCE(SUM(d.pts_amarillas),       0) AS pts_J,
        COALESCE(SUM(d.pts_rojas),           0) AS pts_K,
        COALESCE(SUM(d.pts_var),             0) AS pts_L,
        COALESCE(SUM(d.pts_penales_partido), 0) AS pts_M,
        COALESCE(SUM(d.pts_minuto),          0) AS pts_N,
        COALESCE(SUM(d.pts_penales_tanda),   0) AS pts_O,
        COALESCE(SUM(d.pts_equipo),          0) AS pts_P
    FROM puntaje_detalle d
    JOIN partido p ON p.id = d.partido_id
    JOIN fase    f ON f.id = p.fase_id
    WHERE f.torneo_id = 2
    GROUP BY d.apostador_id
),
globales AS (
    SELECT
        apostador_id,
        COALESCE(SUM(pts_campeon),        0) AS pts_A,
        COALESCE(SUM(pts_finalistas),     0) AS pts_B,
        COALESCE(SUM(pts_goleador),       0) AS pts_C,
        COALESCE(SUM(pts_peor_equipo),    0) AS pts_D,
        COALESCE(SUM(pts_mayor_goleada),  0) AS pts_E,
        COALESCE(SUM(pts_etapa_paraguay), 0) AS pts_F,
        COALESCE(SUM(pts_goles_paraguay), 0) AS pts_G
    FROM puntaje_global
    WHERE torneo_id = 2
    GROUP BY apostador_id
)
SELECT
    COALESCE(um.username, n.nombre, a.apostador_id::text)         AS apostador,
    COALESCE(um.username, a.apostador_id::text)                   AS username,
    a.apostador_id,
    COALESCE(ip.partidos_finalizados, 0)                          AS partidos_finalizados,
    COALESCE(ip.pts_H, 0)  AS "H_resultado",
    COALESCE(ip.pts_I, 0)  AS "I_marcador",
    COALESCE(ip.pts_J, 0)  AS "J_amarillas",
    COALESCE(ip.pts_K, 0)  AS "K_rojas",
    COALESCE(ip.pts_L, 0)  AS "L_var",
    COALESCE(ip.pts_M, 0)  AS "M_penales_partido",
    COALESCE(ip.pts_N, 0)  AS "N_minuto_gol",
    COALESCE(ip.pts_O, 0)  AS "O_penales_tanda",
    COALESCE(ip.pts_P, 0)  AS "P_equipo_clasifica",
    (COALESCE(ip.pts_H,0)+COALESCE(ip.pts_I,0)+COALESCE(ip.pts_J,0)+
     COALESCE(ip.pts_K,0)+COALESCE(ip.pts_L,0)+COALESCE(ip.pts_M,0)+
     COALESCE(ip.pts_N,0)+COALESCE(ip.pts_O,0)+COALESCE(ip.pts_P,0)) AS subtotal_partidos,
    COALESCE(gl.pts_A, 0)  AS "A_campeon",
    COALESCE(gl.pts_B, 0)  AS "B_finalistas",
    COALESCE(gl.pts_C, 0)  AS "C_goleador",
    COALESCE(gl.pts_D, 0)  AS "D_peor_equipo",
    COALESCE(gl.pts_E, 0)  AS "E_mayor_goleada",
    COALESCE(gl.pts_F, 0)  AS "F_etapa_paraguay",
    COALESCE(gl.pts_G, 0)  AS "G_goles_paraguay",
    (COALESCE(gl.pts_A,0)+COALESCE(gl.pts_B,0)+COALESCE(gl.pts_C,0)+
     COALESCE(gl.pts_D,0)+COALESCE(gl.pts_E,0)+COALESCE(gl.pts_F,0)+
     COALESCE(gl.pts_G,0))                                         AS subtotal_globales,
    (COALESCE(ip.pts_H,0)+COALESCE(ip.pts_I,0)+COALESCE(ip.pts_J,0)+
     COALESCE(ip.pts_K,0)+COALESCE(ip.pts_L,0)+COALESCE(ip.pts_M,0)+
     COALESCE(ip.pts_N,0)+COALESCE(ip.pts_O,0)+COALESCE(ip.pts_P,0)+
     COALESCE(gl.pts_A,0)+COALESCE(gl.pts_B,0)+COALESCE(gl.pts_C,0)+
     COALESCE(gl.pts_D,0)+COALESCE(gl.pts_E,0)+COALESCE(gl.pts_F,0)+
     COALESCE(gl.pts_G,0))                                         AS total_puntos
FROM (
    SELECT DISTINCT apostador_id FROM items_partido
    UNION
    SELECT DISTINCT apostador_id FROM globales
) a
LEFT JOIN usernames     um ON um.apostador_id = a.apostador_id
LEFT JOIN nombres       n  ON n.apostador_id  = a.apostador_id
LEFT JOIN items_partido ip ON ip.apostador_id = a.apostador_id
LEFT JOIN globales      gl ON gl.apostador_id = a.apostador_id
ORDER BY total_puntos DESC;

-- ============================================================
-- Vista v_copamundial_puntajes_det (detalle apostador x partido)
-- ============================================================
DROP VIEW IF EXISTS v_copamundial_puntajes_det;

CREATE VIEW v_copamundial_puntajes_det AS
WITH usernames AS (
    SELECT u.id::int AS apostador_id, u.username
    FROM dblink(
        'host=localhost port=5432 dbname=app_db user=app_user password=superpassword',
        'SELECT id, username FROM users WHERE username IS NOT NULL'
    ) AS u(id bigint, username text)
)
SELECT
    COALESCE(um.username, a.nombre_apostador, a.apostador_id::text) AS apostador,
    COALESCE(um.username, a.apostador_id::text)                     AS username,
    a.apostador_id,
    COALESCE(p.numero_fifa, a.numero_fifa, 0)                       AS numero_fifa,
    p.id                                                             AS partido_id,
    f.nombre                                                         AS fase,
    COALESCE(el.nombre_es, el.nombre)                               AS local,
    p.goles_local,
    p.goles_visitante,
    COALESCE(ev.nombre_es, ev.nombre)                               AS visitante,
    p.estado,

    -- H · Resultado
    CASE
        WHEN p.goles_local IS NULL THEN NULL
        WHEN p.goles_local > p.goles_visitante THEN 'Local'
        WHEN p.goles_local < p.goles_visitante THEN 'Visitante'
        ELSE 'Empate'
    END                                                              AS resultado_real,
    CASE
        WHEN a.pred_local > a.pred_visitante THEN 'Local'
        WHEN a.pred_local < a.pred_visitante THEN 'Visitante'
        ELSE 'Empate'
    END                                                              AS resultado_apuesta,
    COALESCE(pd.pts_resultado, 0)                                   AS resultado_pts,

    -- I · Marcador exacto
    COALESCE(p.goles_local::text,'?') || '-' || COALESCE(p.goles_visitante::text,'?')  AS marcador_real,
    a.pred_local::text || '-' || a.pred_visitante::text                                  AS marcador_apuesta,
    COALESCE(pd.pts_marcador, 0)                                    AS marcador_pts,

    -- J · Tarjetas amarillas
    p.amarillas                                                      AS amarillas_real,
    a.pred_amarillas                                                 AS amarillas_apuesta,
    COALESCE(pd.pts_amarillas, 0)                                   AS amarillas_pts,

    -- K · Tarjetas rojas
    p.rojas                                                          AS rojas_real,
    a.pred_rojas                                                     AS rojas_apuesta,
    COALESCE(pd.pts_rojas, 0)                                       AS rojas_pts,

    -- L · Decisiones VAR
    p.decisiones_var                                                 AS var_real,
    a.pred_var                                                       AS var_apuesta,
    COALESCE(pd.pts_var, 0)                                         AS var_pts,

    -- M · Penales cobrados durante el partido
    p.penales_partido                                                AS penales_partido_real,
    a.pred_penales_partido                                           AS penales_partido_apuesta,
    COALESCE(pd.pts_penales_partido, 0)                             AS penales_partido_pts,

    -- N · Minuto del primer gol
    p.minuto_primer_gol                                              AS minuto_gol_real,
    a.pred_minuto_gol                                                AS minuto_gol_apuesta,
    COALESCE(pd.pts_minuto, 0)                                      AS minuto_gol_pts,

    -- O · Penales en tanda (KO)
    COALESCE(p.penales_local::text,'') || '-' || COALESCE(p.penales_visitante::text,'')                               AS penales_tanda_real,
    COALESCE(a.pred_penales_local_tanda::text,'') || '-' || COALESCE(a.pred_penales_visitante_tanda::text,'')         AS penales_tanda_apuesta,
    COALESCE(pd.pts_penales_tanda, 0)                               AS penales_tanda_pts,

    -- P · Equipo que clasifica
    p.equipo_clasificado_id                                          AS equipo_clasifica_real,
    a.pred_equipo_clasifica                                          AS equipo_clasifica_apuesta,
    COALESCE(pd.pts_equipo, 0)                                      AS equipo_clasifica_pts,

    -- Total del partido
    (COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
     COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
     COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
     COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0) +
     COALESCE(pd.pts_equipo,0))                                     AS total_partido

FROM apuesta a
LEFT JOIN usernames     um ON um.apostador_id = a.apostador_id
JOIN partido  p  ON p.id  = a.partido_id
JOIN fase     f  ON f.id  = p.fase_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
LEFT JOIN puntaje_detalle pd
       ON pd.partido_id   = a.partido_id
      AND pd.apostador_id = a.apostador_id
WHERE f.torneo_id = 2
  AND p.estado = 'finalizado'
ORDER BY a.apostador_id, COALESCE(p.numero_fifa, a.numero_fifa, 0);
