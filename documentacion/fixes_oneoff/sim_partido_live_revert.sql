-- ============================================================
-- sim_partido_live_revert.sql
-- Revierte la simulacion de P74 Germany vs Paraguay.
-- ============================================================

BEGIN;

-- Resetear partido P74 a estado original
UPDATE partido SET
    estado              = 'programado',
    goles_local         = NULL,
    goles_visitante     = NULL,
    minuto_actual       = NULL,
    minuto_primer_gol   = NULL,
    amarillas           = NULL,
    local_amarillas     = NULL,
    visitante_amarillas = NULL,
    local_rojas         = NULL,
    visitante_rojas     = NULL,
    rojas               = NULL,
    decisiones_var      = NULL,
    penales_partido     = NULL
WHERE numero_fifa = 74;

-- Borrar apuestas de simulacion para P74
DELETE FROM apuesta
WHERE partido_id = (SELECT id FROM partido WHERE numero_fifa = 74);

SELECT 'Revert OK' AS status, numero_fifa, estado
FROM partido WHERE numero_fifa = 74;

COMMIT;
