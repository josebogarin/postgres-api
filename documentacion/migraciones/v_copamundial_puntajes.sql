-- Vista v_copamundial_puntajes — torneo_id = 2
-- El nombre del apostador se obtiene como alias (username) via dblink a app_db.
-- Fallback: nombre_apostador de apuesta, luego apostador_id::text

CREATE EXTENSION IF NOT EXISTS dblink;

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
    -- Toma el nombre más reciente guardado en apuesta para cada apostador (fallback)
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
