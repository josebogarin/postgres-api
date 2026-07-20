-- fix_swap_predicciones.sql
-- ============================================================
-- Corrige el swap de predicciones para los 5 pares de partidos
-- cuyo numero_fifa fue intercambiado en sesión 58.
--
-- Al momento del import original las predicciones quedaron
-- ligadas al partido_id equivocado porque el numero_fifa
-- estaba invertido. Este script intercambia los pred_* entre
-- los dos partidos de cada par para todos los apostadores.
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\fix_swap_predicciones.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- ── Helper macro: swap pred_* entre dos partido_ids ────────────
-- Repetido 5 veces (una por par swap)

-- Par 1: P049 Scotland/Brazil (pid=194) ↔ P050 Morocco/Haiti (pid=193)
WITH orig AS (
    SELECT apostador_id, partido_id,
           pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas,
           pred_penales_partido, pred_minuto_gol,
           pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica
    FROM apuesta WHERE partido_id IN (194, 193)
),
upd_a AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 194 AND o.partido_id = 193
    RETURNING a.apostador_id
),
upd_b AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 193 AND o.partido_id = 194
    RETURNING a.apostador_id
)
SELECT 'Par1 P049/P050' AS par, COUNT(*) AS apostadores_swapped FROM upd_a;

-- Par 2: P055 Curaçao/Ivory Coast (pid=198) ↔ P056 Ecuador/Germany (pid=197)
WITH orig AS (
    SELECT apostador_id, partido_id,
           pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas,
           pred_penales_partido, pred_minuto_gol,
           pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica
    FROM apuesta WHERE partido_id IN (198, 197)
),
upd_a AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 198 AND o.partido_id = 197
    RETURNING a.apostador_id
),
upd_b AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 197 AND o.partido_id = 198
    RETURNING a.apostador_id
)
SELECT 'Par2 P055/P056' AS par, COUNT(*) AS apostadores_swapped FROM upd_a;

-- Par 3: P061 Norway/France (pid=204) ↔ P062 Senegal/Iraq (pid=203)
WITH orig AS (
    SELECT apostador_id, partido_id,
           pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas,
           pred_penales_partido, pred_minuto_gol,
           pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica
    FROM apuesta WHERE partido_id IN (204, 203)
),
upd_a AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 204 AND o.partido_id = 203
    RETURNING a.apostador_id
),
upd_b AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 203 AND o.partido_id = 204
    RETURNING a.apostador_id
)
SELECT 'Par3 P061/P062' AS par, COUNT(*) AS apostadores_swapped FROM upd_a;

-- Par 4: P065 Cape Verde/Saudi Arabia (pid=206) ↔ P066 Uruguay/Spain (pid=205)
WITH orig AS (
    SELECT apostador_id, partido_id,
           pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas,
           pred_penales_partido, pred_minuto_gol,
           pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica
    FROM apuesta WHERE partido_id IN (206, 205)
),
upd_a AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 206 AND o.partido_id = 205
    RETURNING a.apostador_id
),
upd_b AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 205 AND o.partido_id = 206
    RETURNING a.apostador_id
)
SELECT 'Par4 P065/P066' AS par, COUNT(*) AS apostadores_swapped FROM upd_a;

-- Par 5: P067 Panama/England (pid=210) ↔ P068 Croatia/Ghana (pid=209)
WITH orig AS (
    SELECT apostador_id, partido_id,
           pred_local, pred_visitante, pred_amarillas, pred_var, pred_rojas,
           pred_penales_partido, pred_minuto_gol,
           pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica
    FROM apuesta WHERE partido_id IN (210, 209)
),
upd_a AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 210 AND o.partido_id = 209
    RETURNING a.apostador_id
),
upd_b AS (
    UPDATE apuesta a
    SET pred_local = o.pred_local, pred_visitante = o.pred_visitante,
        pred_amarillas = o.pred_amarillas, pred_var = o.pred_var, pred_rojas = o.pred_rojas,
        pred_penales_partido = o.pred_penales_partido, pred_minuto_gol = o.pred_minuto_gol,
        pred_penales_local_tanda = o.pred_penales_local_tanda,
        pred_penales_visitante_tanda = o.pred_penales_visitante_tanda,
        pred_equipo_clasifica = o.pred_equipo_clasifica
    FROM orig o
    WHERE a.apostador_id = o.apostador_id AND a.partido_id = 209 AND o.partido_id = 210
    RETURNING a.apostador_id
)
SELECT 'Par5 P067/P068' AS par, COUNT(*) AS apostadores_swapped FROM upd_a;

COMMIT;
