-- Vista v_copamundial_puntajes_det — torneo_id = 2
-- Una fila por apostador × partido con columnas descriptivas por ítem.
-- Nombre mostrado: username (alias) via dblink a app_db, fallback nombre_apostador.

CREATE EXTENSION IF NOT EXISTS dblink;

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
    -- Identificación
    COALESCE(um.username, a.nombre_apostador, a.apostador_id::text) AS apostador,
    COALESCE(um.username, a.apostador_id::text)                     AS username,
    a.apostador_id,
    COALESCE(p.numero_fifa, a.numero_fifa, 0)                   AS numero_fifa,
    p.id                                                         AS partido_id,
    f.nombre                                                     AS fase,
    COALESCE(el.nombre_es, el.nombre)                           AS local,
    p.goles_local,
    p.goles_visitante,
    COALESCE(ev.nombre_es, ev.nombre)                           AS visitante,
    p.estado,

    -- H · Resultado (ganador del partido)
    CASE
        WHEN p.goles_local IS NULL THEN NULL
        WHEN p.goles_local > p.goles_visitante THEN 'Local'
        WHEN p.goles_local < p.goles_visitante THEN 'Visitante'
        ELSE 'Empate'
    END                                                          AS resultado_real,
    CASE
        WHEN a.pred_local > a.pred_visitante THEN 'Local'
        WHEN a.pred_local < a.pred_visitante THEN 'Visitante'
        ELSE 'Empate'
    END                                                          AS resultado_apuesta,
    COALESCE(pd.pts_resultado, 0)                               AS resultado_pts,

    -- I · Marcador exacto
    COALESCE(p.goles_local::text,'?') || '-' || COALESCE(p.goles_visitante::text,'?')  AS marcador_real,
    a.pred_local::text || '-' || a.pred_visitante::text                                 AS marcador_apuesta,
    COALESCE(pd.pts_marcador, 0)                                AS marcador_pts,

    -- J · Tarjetas amarillas
    p.amarillas                                                  AS amarillas_real,
    a.pred_amarillas                                             AS amarillas_apuesta,
    COALESCE(pd.pts_amarillas, 0)                               AS amarillas_pts,

    -- K · Tarjetas rojas
    p.rojas                                                      AS rojas_real,
    a.pred_rojas                                                 AS rojas_apuesta,
    COALESCE(pd.pts_rojas, 0)                                   AS rojas_pts,

    -- L · Decisiones VAR
    p.decisiones_var                                             AS var_real,
    a.pred_var                                                   AS var_apuesta,
    COALESCE(pd.pts_var, 0)                                     AS var_pts,

    -- M · Penales cobrados durante el partido
    p.penales_partido                                            AS penales_partido_real,
    a.pred_penales_partido                                       AS penales_partido_apuesta,
    COALESCE(pd.pts_penales_partido, 0)                         AS penales_partido_pts,

    -- N · Minuto del primer gol
    p.minuto_primer_gol                                          AS minuto_gol_real,
    a.pred_minuto_gol                                            AS minuto_gol_apuesta,
    COALESCE(pd.pts_minuto, 0)                                  AS minuto_gol_pts,

    -- O · Penales en tanda (KO)
    COALESCE(p.penales_local::text,'') || '-' || COALESCE(p.penales_visitante::text,'')                                    AS penales_tanda_real,
    COALESCE(a.pred_penales_local_tanda::text,'') || '-' || COALESCE(a.pred_penales_visitante_tanda::text,'')              AS penales_tanda_apuesta,
    COALESCE(pd.pts_penales_tanda, 0)                           AS penales_tanda_pts,

    -- P · Equipo que clasifica
    p.equipo_clasificado_id                                      AS equipo_clasifica_real,
    a.pred_equipo_clasifica                                      AS equipo_clasifica_apuesta,
    COALESCE(pd.pts_equipo, 0)                                  AS equipo_clasifica_pts,

    -- Total del partido
    (COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
     COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
     COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
     COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0) +
     COALESCE(pd.pts_equipo,0))                                 AS total_partido

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
