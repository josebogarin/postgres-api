-- ============================================================
-- Depuración y vistas analytics - base becbuc
-- Fecha: 2026-06-05
--
-- PASO 1 — Elimina tablas no utilizadas por el portal
-- PASO 2 — Crea vistas relacionales con prefijo V_
--
-- Ejecutar en becbuc:
--   Get-Content "C:\proyecto FAST API\documentacion\depuracion_vistas_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

-- ════════════════════════════════════════════════════════════════
-- PASO 1: ELIMINAR TABLAS NO UTILIZADAS
-- ════════════════════════════════════════════════════════════════

-- Tablas de estadísticas y eventos de partido
-- No están referenciadas en ningún endpoint del portal BECBUC.
-- Si se desea implementar detalle de partidos en el futuro,
-- recrearlas desde migracion_becbuc_db.sql.
DROP TABLE IF EXISTS partido_estadistica CASCADE;
DROP TABLE IF EXISTS partido_evento      CASCADE;

-- Tablas plurales (schema BECBUC/fixture_sync.py)
-- Usadas exclusivamente por fixture_sync.py de openfootball.
-- El portal usa las tablas singulares (partido, equipo, fase...).
DROP TABLE IF EXISTS partidos    CASCADE;
DROP TABLE IF EXISTS equipos     CASCADE;
DROP TABLE IF EXISTS grupos      CASCADE;
DROP TABLE IF EXISTS fases       CASCADE;
DROP TABLE IF EXISTS competencias CASCADE;

-- ════════════════════════════════════════════════════════════════
-- PASO 2: CREAR VISTAS ANALYTICS CON PREFIJO V_
-- ════════════════════════════════════════════════════════════════

-- Eliminamos si existen para poder recrearlas limpias
DROP VIEW IF EXISTS V_HECHOS_APUESTAS   CASCADE;
DROP VIEW IF EXISTS V_RANKING_TORNEO    CASCADE;
DROP VIEW IF EXISTS V_RESUMEN_PARTIDO   CASCADE;
DROP VIEW IF EXISTS V_STANDINGS_GRUPOS  CASCADE;
DROP VIEW IF EXISTS V_CALENDARIO        CASCADE;
DROP VIEW IF EXISTS V_DIM_PARTIDO       CASCADE;
DROP VIEW IF EXISTS V_DIM_FASE          CASCADE;
DROP VIEW IF EXISTS V_DIM_EQUIPO        CASCADE;
DROP VIEW IF EXISTS V_DIM_TORNEO        CASCADE;

-- ────────────────────────────────────────────────────────────────
-- DIMENSIONES
-- Vistas descriptivas que enriquecen las claves con atributos.
-- Úsalas como tablas de lookup en análisis y reportes.
-- ────────────────────────────────────────────────────────────────

-- V_DIM_TORNEO
-- Torneo con datos de su competición.
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

COMMENT ON VIEW V_DIM_TORNEO IS
'Dimensión torneo: une torneo con su competición. Filtro: competición activa.';

-- ────────────────────────────────────────────────────────────────

-- V_DIM_EQUIPO
-- Equipo con todos sus atributos de tiebreaker y presentación.
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
    'https://flagcdn.com/w20/' || LOWER(COALESCE(e.codigo_iso,'')) || '.png'
                                                    AS flag_url
FROM equipo e;

COMMENT ON VIEW V_DIM_EQUIPO IS
'Dimensión equipo: atributos completos incluyendo ranking FIFA, fair play y URL de bandera.';

-- ────────────────────────────────────────────────────────────────

-- V_DIM_FASE
-- Fase con contexto de torneo y competición.
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

COMMENT ON VIEW V_DIM_FASE IS
'Dimensión fase: enriquece fase con torneo y competición.';

-- ────────────────────────────────────────────────────────────────

-- V_DIM_PARTIDO
-- Partido con nombres de equipos, fase, torneo y resultado.
-- Calcula resultado real (local/visitante/empate) cuando el partido terminó.
CREATE VIEW V_DIM_PARTIDO AS
SELECT
    p.id                                                AS partido_id,
    p.api_fixture_id,
    p.jornada,
    p.fecha,
    p.sede                                              AS estadio,
    p.ciudad,
    p.estado                                            AS partido_estado,

    -- Equipos
    p.equipo_local_id,
    el.nombre                                           AS local_nombre,
    COALESCE(el.nombre_es, el.nombre)                   AS local_nombre_es,
    COALESCE(el.codigo_iso, '')                         AS local_codigo_iso,
    p.equipo_visitante_id,
    ev.nombre                                           AS visitante_nombre,
    COALESCE(ev.nombre_es, ev.nombre)                   AS visitante_nombre_es,
    COALESCE(ev.codigo_iso, '')                         AS visitante_codigo_iso,

    -- Resultado
    p.goles_local,
    p.goles_visitante,
    CASE
        WHEN p.goles_local IS NULL OR p.goles_visitante IS NULL THEN NULL
        WHEN p.goles_local  > p.goles_visitante THEN 'local'
        WHEN p.goles_local  < p.goles_visitante THEN 'visitante'
        ELSE 'empate'
    END                                                 AS resultado_real,
    p.goles_local - p.goles_visitante                   AS diferencia_goles,

    -- Penales/prórroga
    p.penales_local,
    p.penales_visitante,
    p.goles_local_prorroga,
    p.goles_visitante_prorroga,

    -- Fase / Torneo
    f.id                                                AS fase_id,
    f.nombre                                            AS fase_nombre,
    f.tipo                                              AS fase_tipo,
    f.orden                                             AS fase_orden,
    t.id                                                AS torneo_id,
    t.anio,
    t.nombre                                            AS torneo_nombre,
    c.nombre                                            AS competicion_nombre

FROM partido p
JOIN equipo   el ON el.id = p.equipo_local_id
JOIN equipo   ev ON ev.id = p.equipo_visitante_id
JOIN fase      f ON f.id  = p.fase_id
JOIN torneo    t ON t.id  = p.torneo_id
JOIN competicion c ON c.id = t.competicion_id;

COMMENT ON VIEW V_DIM_PARTIDO IS
'Dimensión partido: join completo con equipos, fase, torneo y resultado calculado.';

-- ────────────────────────────────────────────────────────────────
-- HECHOS Y MÉTRICAS
-- ────────────────────────────────────────────────────────────────

-- V_HECHOS_APUESTAS
-- Tabla de hechos central: cada fila = una apuesta de un apostador.
-- Incluye pronóstico, resultado real, si acertó ganador/marcador, y puntos.
CREATE VIEW V_HECHOS_APUESTAS AS
SELECT
    a.id                                                AS apuesta_id,
    a.apostador_id,
    a.created_at                                        AS apuesta_fecha,
    a.updated_at                                        AS apuesta_ultima_mod,

    -- Pronóstico
    a.pred_local,
    a.pred_visitante,
    a.pred_ganador,

    -- Puntos otorgados
    a.puntos,

    -- Indicadores derivados
    CASE WHEN a.pred_ganador = dp.resultado_real THEN TRUE ELSE FALSE END AS acierto_ganador,
    CASE
        WHEN a.pred_local = dp.goles_local
         AND a.pred_visitante = dp.goles_visitante
        THEN TRUE ELSE FALSE
    END                                                 AS acierto_exacto,

    -- Partido
    dp.partido_id,
    dp.api_fixture_id,
    dp.jornada,
    dp.fecha                                            AS partido_fecha,
    dp.partido_estado,
    dp.resultado_real,
    dp.goles_local                                      AS resultado_local,
    dp.goles_visitante                                  AS resultado_visitante,

    -- Equipos
    dp.equipo_local_id,
    dp.local_nombre_es                                  AS local_nombre,
    dp.local_codigo_iso,
    dp.equipo_visitante_id,
    dp.visitante_nombre_es                              AS visitante_nombre,
    dp.visitante_codigo_iso,

    -- Fase / Torneo
    dp.fase_id,
    dp.fase_nombre,
    dp.fase_tipo,
    dp.torneo_id,
    dp.anio                                             AS torneo_anio,
    dp.torneo_nombre,
    dp.competicion_nombre

FROM apuesta a
JOIN V_DIM_PARTIDO dp ON dp.partido_id = a.partido_id;

COMMENT ON VIEW V_HECHOS_APUESTAS IS
'Hechos de apuestas: fila por apuesta con pronóstico, resultado, aciertos y puntos. Base para todos los análisis de rendimiento.';

-- ────────────────────────────────────────────────────────────────

-- V_RANKING_TORNEO
-- Ranking consolidado de apostadores por torneo.
-- Métricas: total puntos, apuestas registradas, partidos con resultado, aciertos.
CREATE VIEW V_RANKING_TORNEO AS
SELECT
    ha.apostador_id,
    ha.torneo_id,
    ha.torneo_nombre,
    ha.torneo_anio,
    ha.competicion_nombre,

    COUNT(*)                                            AS total_apuestas,
    COUNT(*) FILTER (WHERE ha.resultado_real IS NOT NULL)
                                                        AS partidos_con_resultado,
    COALESCE(SUM(ha.puntos), 0)                         AS puntos_totales,
    COUNT(*) FILTER (WHERE ha.acierto_ganador = TRUE)   AS aciertos_ganador,
    COUNT(*) FILTER (WHERE ha.acierto_exacto  = TRUE)   AS aciertos_exacto,

    -- % efectividad sobre partidos jugados
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE ha.acierto_ganador = TRUE)
        / NULLIF(COUNT(*) FILTER (WHERE ha.resultado_real IS NOT NULL), 0),
        1
    )                                                   AS pct_acierto_ganador,

    DENSE_RANK() OVER (
        PARTITION BY ha.torneo_id
        ORDER BY COALESCE(SUM(ha.puntos), 0) DESC
    )                                                   AS posicion

FROM V_HECHOS_APUESTAS ha
GROUP BY
    ha.apostador_id,
    ha.torneo_id,
    ha.torneo_nombre,
    ha.torneo_anio,
    ha.competicion_nombre;

COMMENT ON VIEW V_RANKING_TORNEO IS
'Ranking de apostadores por torneo: puntos totales, aciertos y posición. Una fila por (apostador, torneo).';

-- ────────────────────────────────────────────────────────────────

-- V_RESUMEN_PARTIDO
-- Por cada partido: cuántos apostaron cada resultado, cuántos acertaron,
-- y distribución porcentual de pronósticos.
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

    -- Distribución porcentual
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'local')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_local,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'empate')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_empate,
    ROUND(100.0 * COUNT(*) FILTER (WHERE ha.pred_ganador = 'visitante')
          / NULLIF(COUNT(*), 0), 1)                                 AS pct_pred_visitante,

    -- Marcador más apostado
    MODE() WITHIN GROUP (
        ORDER BY CONCAT(ha.pred_local, '-', ha.pred_visitante)
    )                                                               AS marcador_mas_apostado

FROM V_HECHOS_APUESTAS ha
GROUP BY
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
    ha.resultado_visitante;

COMMENT ON VIEW V_RESUMEN_PARTIDO IS
'Resumen por partido: distribución de pronósticos, aciertos y marcador más apostado.';

-- ────────────────────────────────────────────────────────────────

-- V_STANDINGS_GRUPOS
-- Standings reales de la fase de grupos (tabla participacion)
-- con nombres de equipos y contexto de torneo/fase.
CREATE VIEW V_STANDINGS_GRUPOS AS
SELECT
    par.id                                              AS participacion_id,
    par.grupo,
    par.posicion,

    -- Stats
    par.pj,
    par.pg,
    par.pe,
    par.pp,
    par.gf,
    par.gc,
    par.gf - par.gc                                     AS gd,
    par.pts,
    par.clasifica,

    -- Equipo
    par.equipo_id,
    COALESCE(e.nombre_es, e.nombre)                     AS equipo_nombre,
    e.nombre                                            AS equipo_nombre_oficial,
    COALESCE(e.codigo_iso, '')                          AS codigo_iso,
    COALESCE(e.fifa_ranking, 9999)                      AS fifa_ranking,
    COALESCE(e.fair_play_pts, 0)                        AS fair_play_pts,

    -- Fase
    par.fase_id,
    f.nombre                                            AS fase_nombre,
    f.tipo                                              AS fase_tipo,

    -- Torneo
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

COMMENT ON VIEW V_STANDINGS_GRUPOS IS
'Standings reales de grupos: participacion con atributos de equipo, fase y torneo. Orden: grupo, pts, gd, gf.';

-- ────────────────────────────────────────────────────────────────

-- V_CALENDARIO
-- Todos los partidos ordenados cronológicamente con equipos y estado.
-- Útil para dashboards de agenda y consultas rápidas.
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

    -- Local
    dp.equipo_local_id,
    dp.local_nombre                                     AS local_nombre_oficial,
    dp.local_nombre_es                                  AS local_nombre,
    dp.local_codigo_iso,
    dp.goles_local,

    -- Visitante
    dp.equipo_visitante_id,
    dp.visitante_nombre                                 AS visitante_nombre_oficial,
    dp.visitante_nombre_es                              AS visitante_nombre,
    dp.visitante_codigo_iso,
    dp.goles_visitante,

    -- Resultado / ganador
    dp.resultado_real,
    dp.diferencia_goles,
    dp.penales_local,
    dp.penales_visitante

FROM V_DIM_PARTIDO dp
ORDER BY dp.fecha NULLS LAST, dp.fase_orden, dp.partido_id;

COMMENT ON VIEW V_CALENDARIO IS
'Calendario completo de partidos con equipos, resultados y fase. Orden cronológico.';

-- ════════════════════════════════════════════════════════════════
-- VERIFICACIÓN
-- ════════════════════════════════════════════════════════════════

SELECT
    viewname                AS vista,
    'OK'                    AS estado
FROM pg_views
WHERE viewname LIKE 'v_dim_%' OR viewname LIKE 'v_%'
  AND schemaname = 'public'
ORDER BY viewname;
