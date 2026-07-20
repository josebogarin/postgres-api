-- ============================================================
-- fix_p73_en_juego.sql
-- Marca P73 (South Africa vs Canada) como en_juego.
-- La fecha real del partido es ~17:00 UTC (13:00 ET / 11:00 CR).
-- ============================================================

BEGIN;

UPDATE partido
SET
    estado      = 'en_juego',
    fecha       = '2026-06-28 17:00:00',  -- hora real: 1pm ET = 17:00 UTC
    minuto_actual = 1
WHERE numero_fifa = 73;

SELECT numero_fifa, estado, fecha, equipo_local_id, equipo_visitante_id
FROM partido WHERE numero_fifa = 73;

COMMIT;
