-- ============================================================
-- Vistas analytics + auditoría BECBUC — script autosuficiente
-- Fecha: 2026-06-05
--
-- Agrega columnas faltantes en equipo, elimina vistas previas
-- y recrea TODAS las vistas (base + auditoría) en un solo paso.
--
-- Ejecutar en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\vistas_auditoria_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
--
-- NOTA apostador_id:
--   Referencia lógica a app_db.users(id). El nombre del apostador
--   debe resolverse desde la app o BI conectando ambas BDs.
-- ============================================================

-- ════════════════════════════════════════════════════════════════
-- PASO 1: COLUMNAS FALTANTES EN equipo
-- ════════════════════════════════════════════════════════════════

ALTER TABLE equipo ADD COLUMN IF NOT EXISTS codigo_iso    VARCHAR(10);
ALTER TABLE equipo ADD COLUMN IF NOT EXISTS fifa_ranking  INTEGER;
ALTER TABLE equipo ADD COLUMN IF NOT EXISTS fair_play_pts INTEGER DEFAULT 0;

-- ════════════════════════════════════════════════════════════════
-- PASO 2: DROP DE TODAS LAS VISTAS (en orden de dependencia)
-- ════════════════════════════════════════════════════════════════

DROP VIEW IF EXISTS V_MEJORES_TERCEROS      CASCADE;
DROP VIEW IF EXISTS V_AUDITORIA_PUNTAJES    CASCADE;
DROP VIEW IF EXISTS V_AUDITORIA_PRONOSTICOS CASCADE;
DROP VIEW IF EXISTS V_RANKING_TORNEO        CASCADE;
DROP VIEW IF EXISTS V_RESUMEN_PARTIDO       CASCADE;
DROP VIEW IF EXISTS V_STANDINGS_GRUPOS      CASCADE;
DROP VIEW IF EXISTS V_CALENDARIO            CASCADE;
DROP VIEW IF EXISTS V_HECHOS_APUESTAS       CASCADE;
DROP VIEW IF EXISTS V_DIM_PARTIDO           CASCADE;
DROP VIEW IF EXISTS V_DIM_FASE              CASCADE;
DROP VIEW IF EXISTS V_DIM_EQUIPO            CASCADE;
DROP VIEW IF EXISTS V_DIM_TORNEO            CASCADE;

-- ════════════════════════════════════════════════════════════════
-- PASO 3: VISTAS DIMENSIONALES (base)
-- ════════════════════════════════════════════════════════════════

CREATE VIEW V_DIM_TORNEO AS
SELECT
    t.id                        AS torneo_id,
    t.anio,
    t.nombre                    AS torneo_nombre,
    t.sede                      AS torneo_sede,
    t.estado                    AS torneo_estado,
    t.datos_cargados,
    t.apuesta_inicio,
    t.apuesta_fin,
    c.id                        AS competicion_id,
    c.nombre                    AS competicion_nombre,
    c.nombre_corto              AS competicion_sigla,
    c.tipo                      AS competicion_tipo,
    c.emoji                     AS competicion_emoji
FROM torneo t
JOIN competicion c ON c.id = t.competicion_id
WHERE c.es_activo = TRUE;

COMMENT ON VIEW V_DIM_TORNEO IS 'Dimensión torneo + competición.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_DIM_EQUIPO AS
SELECT
    e.id                                            AS equipo_id,
    e.api_team_id,
    e.nombre,
    COALESCE(e.nombre_es, e.nombre)                 AS nombre_display,
    e.pais,
    e.logo_url,
    COALESCE(e.codigo_iso, '')                      AS codigo_iso,
    COALESCE(e.fifa_ranking, 9999)                  AS fifa_ranking,
    COALESCE(e.fair_play_pts, 0)                    AS fair_play_pts,
    'https://flagcdn.com/w20/' || LOWER(COALESCE(e.codigo_iso,'')) || '.png' AS flag_url
FROM equipo e;

COMMENT ON VIEW V_DIM_EQUIPO IS 'Dimensión equipo con ranking FIFA, fair play y URL de bandera.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_DIM_FASE AS
SELECT
    f.id                        AS fase_id,
    f.nombre                    AS fase_nombre,
    f.tipo                      AS fase_tipo,
    f.orden                     AS fase_orden,
    f.visible_apostador,
    t.id                        AS torneo_id,
    t.anio,
    t.nombre                    AS torneo_nombre,
    t.estado                    AS torneo_estado,
    c.nombre                    AS competicion_nombre,
    c.nombre_corto              AS competicion_sigla
FROM fase f
JOIN torneo t      ON t.id = f.torneo_id
JOIN competicion c ON c.id = t.competicion_id;

COMMENT ON VIEW V_DIM_FASE IS 'Dimensión fase + torneo + competición.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_DIM_PARTIDO AS
SELECT
    p.id                                                AS partido_id,
    p.api_fixture_id,
    p.jornada,
    p.fecha,
    p.sede                                              AS estadio,
    p.ciudad,
    p.estado                                            AS partido_estado,
    p.equipo_local_id,
    el.nombre                                           AS local_nombre,
    COALESCE(el.nombre_es, el.nombre)                   AS local_nombre_es,
    COALESCE(el.codigo_iso, '')                         AS local_codigo_iso,
    el.pais                                             AS local_pais,
    p.equipo_visitante_id,
    ev.nombre                                           AS visitante_nombre,
    COALESCE(ev.nombre_es, ev.nombre)                   AS visitante_nombre_es,
    COALESCE(ev.codigo_iso, '')                         AS visitante_codigo_iso,
    ev.pais                                             AS visitante_pais,
    p.goles_local,
    p.goles_visitante,
    CASE
        WHEN p.goles_local IS NULL OR p.goles_visitante IS NULL THEN NULL
        WHEN p.goles_local  > p.goles_visitante THEN 'local'
        WHEN p.goles_local  < p.goles_visitante THEN 'visitante'
        ELSE 'empate'
    END                                                 AS resultado_real,
    p.goles_local - p.goles_visitante                   AS diferencia_goles,
    p.penales_local,
    p.penales_visitante,
    p.goles_local_prorroga,
    p.goles_visitante_prorroga,
    f.id                                                AS fase_id,
    f.nombre                                            AS fase_nombre,
    f.tipo                                              AS fase_tipo,
    f.orden                                             AS fase_orden,
    t.id                                                AS torneo_id,
    t.anio,
    t.nombre                                            AS torneo_nombre,
    c.nombre                                            AS competicion_nombre
FROM partido p
JOIN equipo      el ON el.id = p.equipo_local_id
JOIN equipo      ev ON ev.id = p.equipo_visitante_id
JOIN fase         f ON f.id  = p.fase_id
JOIN torneo       t ON t.id  = p.torneo_id
JOIN competicion  c ON c.id  = t.competicion_id;

COMMENT ON VIEW V_DIM_PARTIDO IS 'Partido con equipos, resultado calculado, fase y torneo.';

-- ════════════════════════════════════════════════════════════════
-- PASO 4: VISTAS DE HECHOS Y MÉTRICAS
-- ════════════════════════════════════════════════════════════════

CREATE VIEW V_HECHOS_APUESTAS AS
SELECT
    a.id                                                AS apuesta_id,
    a.apostador_id,
    a.created_at                                        AS apuesta_fecha,
    a.updated_at                                        AS apuesta_ultima_mod,
    a.pred_local,
    a.pred_visitante,
    a.pred_ganador,
    a.puntos,
    CASE WHEN a.pred_ganador = dp.resultado_real THEN TRUE ELSE FALSE END AS acierto_ganador,
    CASE
        WHEN a.pred_local = dp.goles_local AND a.pred_visitante = dp.goles_visitante
        THEN TRUE ELSE FALSE
    END                                                 AS acierto_exacto,
    dp.partido_id,
    dp.api_fixture_id,
    dp.jornada,
    dp.fecha                                            AS partido_fecha,
    dp.partido_estado,
    dp.resultado_real,
    dp.goles_local                                      AS resultado_local,
    dp.goles_visitante                                  AS resultado_visitante,
    dp.equipo_local_id,
    dp.local_nombre_es                                  AS local_nombre,
    dp.local_codigo_iso,
    dp.local_pais,
    dp.equipo_visitante_id,
    dp.visitante_nombre_es                              AS visitante_nombre,
    dp.visitante_codigo_iso,
    dp.visitante_pais,
    dp.fase_id,
    dp.fase_nombre,
    dp.fase_tipo,
    dp.torneo_id,
    dp.anio                                             AS torneo_anio,
    dp.torneo_nombre,
    dp.competicion_nombre
FROM apuesta a
JOIN V_DIM_PARTIDO dp ON dp.partido_id = a.partido_id;

COMMENT ON VIEW V_HECHOS_APUESTAS IS 'Tabla de hechos: apuesta × partido con aciertos y puntos.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_RANKING_TORNEO AS
SELECT
    ha.apostador_id,
    ha.torneo_id,
    ha.torneo_nombre,
    ha.torneo_anio,
    ha.competicion_nombre,
    COUNT(*)                                                        AS total_apuestas,
    COUNT(*) FILTER (WHERE ha.resultado_real IS NOT NULL)           AS partidos_con_resultado,
    COALESCE(SUM(ha.puntos), 0)                                     AS puntos_totales,
    COUNT(*) FILTER (WHERE ha.acierto_ganador = TRUE)               AS aciertos_ganador,
    COUNT(*) FILTER (WHERE ha.acierto_exacto  = TRUE)               AS aciertos_exacto,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE ha.acierto_ganador = TRUE)
        / NULLIF(COUNT(*) FILTER (WHERE ha.resultado_real IS NOT NULL), 0), 1
    )                                                               AS pct_acierto_ganador,
    DENSE_RANK() OVER (
        PARTITION BY ha.torneo_id
        ORDER BY COALESCE(SUM(ha.puntos), 0) DESC
    )                                                               AS posicion
FROM V_HECHOS_APUESTAS ha
GROUP BY ha.apostador_id, ha.torneo_id, ha.torneo_nombre, ha.torneo_anio, ha.competicion_nombre;

COMMENT ON VIEW V_RANKING_TORNEO IS 'Ranking de apostadores por torneo con puntos, aciertos y posición.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_RESUMEN_PARTIDO AS
SELECT
    ha.partido_id,
    ha.partido_fecha,
    ha.partido_estado,
    ha.fase_nombre,
    ha.fase_tipo,
    ha.torneo_id,
    ha.torneo_nombre,
    ha.local_nombre,
    ha.visitante_nombre,
    ha.local_codigo_iso,
    ha.visitante_codigo_iso,
    ha.resultado_real,
    ha.resultado_local,
    ha.resultado_visitante,
    COUNT(*)                                                        AS total_apuestas,
    COUNT(*) FILTER (WHERE ha.pred_ganador = 'local')               AS pred_local_cnt,
    COUNT(*) FILTER (WHERE ha.pred_ganador = 'empate')              AS pred_empate_cnt,
    COUNT(*) FILTER (WHERE ha.pred_ganador = 'visitante')           AS pred_visitante_cnt,
    COUNT(*) FILTER (WHERE ha.acierto_ganador = TRUE)               AS aciertos_ganador,
    COUNT(*) FILTER (WHERE ha.acierto_exacto  = TRUE)               AS aciertos_exacto,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'local')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_local,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'empate')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_empate,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'visitante')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_visitante,
    MODE() WITHIN GROUP (ORDER BY CONCAT(ha.pred_local, '-', ha.pred_visitante)) AS marcador_mas_apostado
FROM V_HECHOS_APUESTAS ha
GROUP BY
    ha.partido_id, ha.partido_fecha, ha.partido_estado,
    ha.fase_nombre, ha.fase_tipo, ha.torneo_id, ha.torneo_nombre,
    ha.local_nombre, ha.visitante_nombre, ha.local_codigo_iso, ha.visitante_codigo_iso,
    ha.resultado_real, ha.resultado_local, ha.resultado_visitante;

COMMENT ON VIEW V_RESUMEN_PARTIDO IS 'Distribución de pronósticos y aciertos por partido.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_STANDINGS_GRUPOS AS
SELECT
    par.id                                              AS participacion_id,
    par.grupo,
    par.posicion,
    par.pj, par.pg, par.pe, par.pp,
    par.gf, par.gc,
    par.gf - par.gc                                     AS gd,
    par.pts,
    par.clasifica,
    par.equipo_id,
    COALESCE(e.nombre_es, e.nombre)                     AS equipo_nombre,
    e.nombre                                            AS equipo_nombre_oficial,
    COALESCE(e.codigo_iso, '')                          AS codigo_iso,
    e.pais,
    COALESCE(e.fifa_ranking, 9999)                      AS fifa_ranking,
    COALESCE(e.fair_play_pts, 0)                        AS fair_play_pts,
    par.fase_id,
    f.nombre                                            AS fase_nombre,
    f.tipo                                              AS fase_tipo,
    t.id                                                AS torneo_id,
    t.anio,
    t.nombre                                            AS torneo_nombre,
    c.nombre                                            AS competicion_nombre
FROM participacion par
JOIN equipo        e ON e.id  = par.equipo_id
JOIN fase          f ON f.id  = par.fase_id
JOIN torneo        t ON t.id  = f.torneo_id
JOIN competicion   c ON c.id  = t.competicion_id
ORDER BY par.grupo, par.pts DESC, (par.gf - par.gc) DESC, par.gf DESC;

COMMENT ON VIEW V_STANDINGS_GRUPOS IS 'Standings reales de grupos con atributos de equipo y tiebreaker.';

-- ────────────────────────────────────────────────────────────────

CREATE VIEW V_CALENDARIO AS
SELECT
    dp.partido_id,
    dp.fecha,
    dp.partido_estado,
    dp.jornada,
    dp.estadio,
    dp.ciudad,
    dp.fase_tipo,
    dp.fase_nombre,
    dp.fase_orden,
    dp.torneo_id,
    dp.torneo_nombre,
    dp.anio                                             AS torneo_anio,
    dp.competicion_nombre,
    dp.equipo_local_id,
    dp.local_nombre_es                                  AS local_nombre,
    dp.local_codigo_iso,
    dp.local_pais,
    dp.goles_local,
    dp.equipo_visitante_id,
    dp.visitante_nombre_es                              AS visitante_nombre,
    dp.visitante_codigo_iso,
    dp.visitante_pais,
    dp.goles_visitante,
    dp.resultado_real,
    dp.diferencia_goles,
    dp.penales_local,
    dp.penales_visitante
FROM V_DIM_PARTIDO dp
ORDER BY dp.fecha NULLS LAST, dp.fase_orden, dp.partido_id;

COMMENT ON VIEW V_CALENDARIO IS 'Calendario completo de partidos ordenado cronológicamente.';

-- ════════════════════════════════════════════════════════════════
-- PASO 5: VISTAS DE AUDITORÍA
-- ════════════════════════════════════════════════════════════════

-- V_AUDITORIA_PRONOSTICOS
-- Una fila por pronóstico: apostador, predicción, resultado real,
-- nombres de países, fase y torneo. Base para auditoría.
CREATE VIEW V_AUDITORIA_PRONOSTICOS AS
SELECT
    a.id                                                AS pronostico_id,
    a.apostador_id,

    -- Pronóstico
    a.pred_local,
    a.pred_visitante,
    a.pred_ganador,
    a.created_at                                        AS registrado_en,
    a.updated_at                                        AS modificado_en,

    -- Partido
    p.id                                                AS partido_id,
    p.fecha                                             AS partido_fecha,
    p.estado                                            AS partido_estado,
    p.jornada,

    -- Resultado real
    p.goles_local                                       AS resultado_local,
    p.goles_visitante                                   AS resultado_visitante,
    CASE
        WHEN p.goles_local IS NULL OR p.goles_visitante IS NULL THEN NULL
        WHEN p.goles_local  > p.goles_visitante THEN 'local'
        WHEN p.goles_local  < p.goles_visitante THEN 'visitante'
        ELSE 'empate'
    END                                                 AS resultado_real,

    -- Aciertos
    CASE
        WHEN a.pred_ganador = (
            CASE
                WHEN p.goles_local IS NULL OR p.goles_visitante IS NULL THEN NULL
                WHEN p.goles_local  > p.goles_visitante THEN 'local'
                WHEN p.goles_local  < p.goles_visitante THEN 'visitante'
                ELSE 'empate'
            END) THEN TRUE ELSE FALSE
    END                                                 AS acierto_ganador,
    CASE
        WHEN a.pred_local = p.goles_local AND a.pred_visitante = p.goles_visitante
        THEN TRUE ELSE FALSE
    END                                                 AS acierto_exacto,

    -- Equipo local (nombre del país)
    el.id                                               AS local_id,
    COALESCE(el.nombre_es, el.nombre)                   AS local_nombre,
    el.pais                                             AS local_pais,
    COALESCE(el.codigo_iso, '')                         AS local_iso,

    -- Equipo visitante (nombre del país)
    ev.id                                               AS visitante_id,
    COALESCE(ev.nombre_es, ev.nombre)                   AS visitante_nombre,
    ev.pais                                             AS visitante_pais,
    COALESCE(ev.codigo_iso, '')                         AS visitante_iso,

    -- Fase
    f.id                                                AS fase_id,
    f.nombre                                            AS fase_nombre,
    f.tipo                                              AS fase_tipo,
    f.orden                                             AS fase_orden,

    -- Torneo
    t.id                                                AS torneo_id,
    t.anio                                              AS torneo_anio,
    t.nombre                                            AS torneo_nombre,
    c.nombre                                            AS competicion_nombre

FROM apuesta a
JOIN partido      p  ON p.id  = a.partido_id
JOIN equipo       el ON el.id = p.equipo_local_id
JOIN equipo       ev ON ev.id = p.equipo_visitante_id
JOIN fase          f ON f.id  = p.fase_id
JOIN torneo        t ON t.id  = p.torneo_id
JOIN competicion   c ON c.id  = t.competicion_id;

COMMENT ON VIEW V_AUDITORIA_PRONOSTICOS IS
'Auditoría de pronósticos: una fila por apostador×partido con nombres de países, '
'fase, torneo y aciertos. apostador_id → app_db.users(id).';

-- ────────────────────────────────────────────────────────────────

-- V_AUDITORIA_PUNTAJES
-- Puntos obtenidos por partido + acumulado corrido + posición en torneo.
-- Nota: window functions anidadas no son válidas en PostgreSQL;
-- se usa CTE intermedio para calcular el total antes del DENSE_RANK.
CREATE VIEW V_AUDITORIA_PUNTAJES AS
WITH base AS (
    SELECT
        vp.apostador_id,
        vp.torneo_id,
        vp.torneo_anio,
        vp.torneo_nombre,
        vp.competicion_nombre,
        vp.fase_nombre,
        vp.fase_tipo,
        vp.fase_orden,
        vp.partido_id,
        vp.partido_fecha,
        vp.partido_estado,
        vp.jornada,
        vp.local_nombre,
        vp.local_pais,
        vp.local_iso,
        vp.visitante_nombre,
        vp.visitante_pais,
        vp.visitante_iso,
        vp.pred_local,
        vp.pred_visitante,
        vp.pred_ganador,
        vp.resultado_local,
        vp.resultado_visitante,
        vp.resultado_real,
        vp.acierto_ganador,
        vp.acierto_exacto,
        COALESCE(a.puntos, 0)                               AS puntos_partido,
        SUM(COALESCE(a.puntos, 0)) OVER (
            PARTITION BY vp.apostador_id, vp.torneo_id
            ORDER BY vp.partido_fecha NULLS LAST, vp.partido_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                   AS puntos_acumulados,
        SUM(COALESCE(a.puntos, 0)) OVER (
            PARTITION BY vp.apostador_id, vp.torneo_id
        )                                                   AS puntos_totales,
        vp.registrado_en,
        vp.modificado_en
    FROM V_AUDITORIA_PRONOSTICOS vp
    JOIN apuesta a ON a.id = vp.pronostico_id
)
SELECT
    apostador_id,
    torneo_id,
    torneo_anio,
    torneo_nombre,
    competicion_nombre,
    fase_nombre,
    fase_tipo,
    fase_orden,
    partido_id,
    partido_fecha,
    partido_estado,
    jornada,
    local_nombre,
    local_pais,
    local_iso,
    visitante_nombre,
    visitante_pais,
    visitante_iso,
    pred_local,
    pred_visitante,
    pred_ganador,
    resultado_local,
    resultado_visitante,
    resultado_real,
    acierto_ganador,
    acierto_exacto,
    puntos_partido,
    puntos_acumulados,
    DENSE_RANK() OVER (
        PARTITION BY torneo_id
        ORDER BY puntos_totales DESC
    )                                                       AS posicion_torneo,
    registrado_en,
    modificado_en
FROM base;

COMMENT ON VIEW V_AUDITORIA_PUNTAJES IS
'Puntajes por partido con acumulado corrido y posición en el torneo. '
'apostador_id → app_db.users(id).';

-- ────────────────────────────────────────────────────────────────

-- V_MEJORES_TERCEROS
-- Terceros puestos reales de cada grupo con criterios de clasificación FIFA.
-- clasifica_r32 = TRUE para los 8 mejores terceros que avanzan a Ronda de 32.
CREATE VIEW V_MEJORES_TERCEROS AS
WITH terceros AS (
    SELECT
        par.grupo,
        par.pts,
        par.gf,
        par.gc,
        par.gf - par.gc                                 AS gd,
        par.pj, par.pg, par.pe, par.pp,
        e.id                                            AS equipo_id,
        COALESCE(e.nombre_es, e.nombre)                 AS equipo_nombre,
        e.pais,
        COALESCE(e.codigo_iso, '')                      AS codigo_iso,
        COALESCE(e.fifa_ranking, 9999)                  AS fifa_ranking,
        COALESCE(e.fair_play_pts, 0)                    AS fair_play_pts,
        f.id                                            AS fase_id,
        f.nombre                                        AS fase_nombre,
        t.id                                            AS torneo_id,
        t.anio                                          AS torneo_anio,
        t.nombre                                        AS torneo_nombre,
        c.nombre                                        AS competicion_nombre,
        ROW_NUMBER() OVER (
            PARTITION BY f.torneo_id
            ORDER BY
                par.pts                          DESC,
                (par.gf - par.gc)                DESC,
                par.gf                           DESC,
                COALESCE(e.fair_play_pts, 0)     ASC,
                COALESCE(e.fifa_ranking, 9999)   ASC
        )                                               AS rank_mejores_terceros
    FROM participacion par
    JOIN equipo       e ON e.id  = par.equipo_id
    JOIN fase         f ON f.id  = par.fase_id
    JOIN torneo       t ON t.id  = f.torneo_id
    JOIN competicion  c ON c.id  = t.competicion_id
    WHERE par.posicion = 3
      AND f.tipo = 'grupo'
)
SELECT
    t.*,
    CASE WHEN t.rank_mejores_terceros <= 8 THEN TRUE ELSE FALSE END AS clasifica_r32
FROM terceros t
ORDER BY t.torneo_id, t.rank_mejores_terceros;

COMMENT ON VIEW V_MEJORES_TERCEROS IS
'Terceros puestos reales ordenados por criterios FIFA. '
'clasifica_r32=TRUE para los 8 mejores que avanzan a la Ronda de 32.';

-- ════════════════════════════════════════════════════════════════
-- VERIFICACIÓN FINAL
-- ════════════════════════════════════════════════════════════════

SELECT viewname AS vista, 'OK' AS estado
FROM pg_views
WHERE schemaname = 'public'
  AND viewname LIKE 'v_%'
ORDER BY viewname;
