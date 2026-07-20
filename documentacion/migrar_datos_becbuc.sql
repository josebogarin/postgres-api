-- ============================================================
-- Migración de datos: app_db → becbuc
-- Ejecutar conectado a BECBUC:
--   Get-Content "C:\proyecto FAST API\documentacion\migrar_datos_becbuc.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

CREATE EXTENSION IF NOT EXISTS dblink;

DO $$
DECLARE
    src text := 'host=localhost port=5432 dbname=app_db user=app_user password=superpassword';
BEGIN

    INSERT INTO competicion (id, api_league_id, nombre, nombre_corto, tipo, formato_playoff, emoji, es_activo)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, api_league_id, nombre, nombre_corto, tipo, formato_playoff, emoji, es_activo FROM competicion'
    ) AS t(id bigint, api_league_id int, nombre varchar, nombre_corto varchar, tipo varchar, formato_playoff varchar, emoji varchar, es_activo bool)
    ON CONFLICT DO NOTHING;

    INSERT INTO equipo (id, api_team_id, nombre, nombre_es, logo_url, pais)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, api_team_id, nombre, nombre_es, logo_url, pais FROM equipo'
    ) AS t(id bigint, api_team_id int, nombre varchar, nombre_es varchar, logo_url varchar, pais varchar)
    ON CONFLICT DO NOTHING;

    INSERT INTO torneo (id, competicion_id, anio, nombre, sede, estado, datos_cargados, api_season)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, competicion_id, anio, nombre, sede, estado, datos_cargados, api_season FROM torneo'
    ) AS t(id bigint, competicion_id bigint, anio int, nombre varchar, sede varchar, estado varchar, datos_cargados bool, api_season int)
    ON CONFLICT DO NOTHING;

    INSERT INTO fase (id, torneo_id, nombre, tipo, orden, visible_apostador)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, torneo_id, nombre, tipo, orden, COALESCE(visible_apostador, true) FROM fase'
    ) AS t(id bigint, torneo_id bigint, nombre varchar, tipo varchar, orden int, visible_apostador bool)
    ON CONFLICT DO NOTHING;

    INSERT INTO partido (id, torneo_id, fase_id, api_fixture_id, jornada, fecha, sede, ciudad,
        estado, equipo_local_id, equipo_visitante_id,
        goles_local, goles_visitante, goles_local_prorroga, goles_visitante_prorroga,
        penales_local, penales_visitante, leg, partido_ida_id)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, torneo_id, fase_id, api_fixture_id, jornada, fecha, sede, ciudad,
         estado, equipo_local_id, equipo_visitante_id,
         goles_local, goles_visitante, goles_local_prorroga, goles_visitante_prorroga,
         penales_local, penales_visitante, leg, partido_ida_id FROM partido'
    ) AS t(id bigint, torneo_id bigint, fase_id bigint, api_fixture_id int, jornada int,
           fecha timestamptz, sede varchar, ciudad varchar, estado varchar,
           equipo_local_id bigint, equipo_visitante_id bigint,
           goles_local int, goles_visitante int, goles_local_prorroga int, goles_visitante_prorroga int,
           penales_local int, penales_visitante int, leg varchar, partido_ida_id bigint)
    ON CONFLICT DO NOTHING;

    INSERT INTO participacion (id, fase_id, equipo_id, posicion, pj, pg, pe, pp, gf, gc, pts, clasifica)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, fase_id, equipo_id, posicion, pj, pg, pe, pp, gf, gc, pts, clasifica FROM participacion'
    ) AS t(id bigint, fase_id bigint, equipo_id bigint, posicion int,
           pj int, pg int, pe int, pp int, gf int, gc int, pts int, clasifica bool)
    ON CONFLICT DO NOTHING;

    INSERT INTO partido_estadistica (id, partido_id, equipo_id, tiros_total, tiros_al_arco,
        posesion, pases_total, pases_precision, faltas, tarjetas_amarillas, tarjetas_rojas,
        fueras_de_juego, corners, datos_extra)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, partido_id, equipo_id, tiros_total, tiros_al_arco, posesion, pases_total,
         pases_precision, faltas, tarjetas_amarillas, tarjetas_rojas, fueras_de_juego, corners, datos_extra
         FROM partido_estadistica'
    ) AS t(id bigint, partido_id bigint, equipo_id bigint, tiros_total int, tiros_al_arco int,
           posesion numeric, pases_total int, pases_precision numeric, faltas int,
           tarjetas_amarillas int, tarjetas_rojas int, fueras_de_juego int, corners int, datos_extra jsonb)
    ON CONFLICT DO NOTHING;

    INSERT INTO partido_evento (id, partido_id, equipo_id, tipo, minuto, minuto_extra,
        jugador_nombre, asistencia_nombre, detalle)
    OVERRIDING SYSTEM VALUE
    SELECT * FROM dblink(src,
        'SELECT id, partido_id, equipo_id, tipo, minuto, minuto_extra,
         jugador_nombre, asistencia_nombre, detalle FROM partido_evento'
    ) AS t(id bigint, partido_id bigint, equipo_id bigint, tipo varchar, minuto int, minuto_extra int,
           jugador_nombre varchar, asistencia_nombre varchar, detalle varchar)
    ON CONFLICT DO NOTHING;

    -- apuesta: se crea vacía en becbuc (tabla nueva, no existía en app_db)

    -- Resetear secuencias
    PERFORM setval(pg_get_serial_sequence('competicion','id'),   COALESCE((SELECT MAX(id) FROM competicion),1));
    PERFORM setval(pg_get_serial_sequence('equipo','id'),        COALESCE((SELECT MAX(id) FROM equipo),1));
    PERFORM setval(pg_get_serial_sequence('torneo','id'),        COALESCE((SELECT MAX(id) FROM torneo),1));
    PERFORM setval(pg_get_serial_sequence('fase','id'),          COALESCE((SELECT MAX(id) FROM fase),1));
    PERFORM setval(pg_get_serial_sequence('partido','id'),       COALESCE((SELECT MAX(id) FROM partido),1));
    PERFORM setval(pg_get_serial_sequence('participacion','id'), COALESCE((SELECT MAX(id) FROM participacion),1));
    PERFORM setval(pg_get_serial_sequence('apuesta','id'),       COALESCE((SELECT MAX(id) FROM apuesta),1));

    RAISE NOTICE 'Migración completada OK';
END $$;
