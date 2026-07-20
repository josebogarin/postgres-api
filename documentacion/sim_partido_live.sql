-- ============================================================
-- sim_partido_live.sql
-- Simula Germany vs Paraguay (P74) en el minuto 67, empate 1-1.
-- Paraguay duplica puntaje. Muestra scoring engine en accion.
-- REVERT: sim_partido_live_revert.sql
-- ============================================================

BEGIN;

-- 1. Partido P74: Germany vs Paraguay → estado en_juego, min 67, 1-1
UPDATE partido SET
    estado             = 'en_juego',
    goles_local        = 1,
    goles_visitante    = 1,
    minuto_actual      = 67,
    minuto_primer_gol  = 23,
    amarillas          = 3,
    local_amarillas    = 2,
    visitante_amarillas= 1,
    local_rojas        = 0,
    visitante_rojas    = 0,
    rojas              = 0,
    decisiones_var     = 1,
    penales_partido    = 0
WHERE numero_fifa = 74;

-- 2. Insertar apuestas variadas para los primeros 12 apostadores
--    Pred A: 2-1 Germany (acierta resultado, falla marcador exacto)
--    Pred B: 1-1 empate (si termina así → marcador exacto)
--    Pred C: 0-2 Paraguay gana (falla resultado)

WITH ap_ids AS (
    SELECT u.id, ROW_NUMBER() OVER (ORDER BY u.id) AS rn
    FROM users u
    JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles ro ON ro.id = ur.role_id
    WHERE ro.name = 'apostador' AND u.is_active = TRUE
    AND u.username != 'jose'
    LIMIT 15
),
partido_data AS (
    SELECT p.id AS pid, p.equipo_local_id AS lid, p.equipo_visitante_id AS vid
    FROM partido p WHERE p.numero_fifa = 74
)
INSERT INTO apuesta (
    apostador_id, partido_id, torneo_id,
    pred_local, pred_visitante,
    pred_amarillas, pred_rojas, pred_var,
    pred_penales_partido, pred_minuto_gol,
    nombre_apostador
)
SELECT
    a.id,
    pd.pid,
    2,
    CASE
        WHEN a.rn % 3 = 0 THEN 1   -- empate 1-1 (marcador exacto si termina asi)
        WHEN a.rn % 3 = 1 THEN 2   -- 2-1 Germany (acierta resultado)
        ELSE 0                       -- 0-2 Paraguay (falla resultado)
    END,
    CASE
        WHEN a.rn % 3 = 0 THEN 1
        WHEN a.rn % 3 = 1 THEN 1
        ELSE 2
    END,
    CASE WHEN a.rn % 4 = 0 THEN 3 WHEN a.rn % 4 = 1 THEN 2 ELSE 1 END, -- amarillas
    0,  -- rojas
    CASE WHEN a.rn % 5 = 0 THEN 1 ELSE 0 END, -- VAR
    0,  -- penales en partido
    CASE WHEN a.rn % 3 = 0 THEN 23 WHEN a.rn % 3 = 1 THEN 30 ELSE 15 END, -- minuto gol
    (SELECT username FROM users WHERE id = a.id)
FROM ap_ids a, partido_data pd
ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
    pred_local            = EXCLUDED.pred_local,
    pred_visitante        = EXCLUDED.pred_visitante,
    pred_amarillas        = EXCLUDED.pred_amarillas,
    pred_rojas            = EXCLUDED.pred_rojas,
    pred_var              = EXCLUDED.pred_var,
    pred_penales_partido  = EXCLUDED.pred_penales_partido,
    pred_minuto_gol       = EXCLUDED.pred_minuto_gol;

-- Verificar
SELECT p.numero_fifa, e1.nombre AS local, p.goles_local,
       p.goles_visitante, e2.nombre AS visitante,
       p.estado, p.minuto_actual, p.amarillas, p.decisiones_var
FROM partido p
JOIN equipo e1 ON e1.id = p.equipo_local_id
JOIN equipo e2 ON e2.id = p.equipo_visitante_id
WHERE p.numero_fifa = 74;

SELECT COUNT(*) AS apuestas_insertadas FROM apuesta
WHERE partido_id = (SELECT id FROM partido WHERE numero_fifa = 74);

COMMIT;
