-- ============================================================
-- reset_ko_resultados.sql
-- Elimina resultados simulados y pronosticos de todas las fases KO.
-- Conserva: equipos (equipo_local_id/visitante_id), apuestas de grupos,
--            puntajes de grupos (fase bloqueada), apostador_clasificados grupos.
-- ============================================================

BEGIN;

-- 1. Eliminar pronosticos (apuesta) de partidos KO
--    Los apostadores aun no hicieron pronosticos reales para KO.
--    Esto limpia cualquier dato de simulacion en la tabla apuesta.
DELETE FROM apuesta
WHERE partido_id IN (
    SELECT p.id FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2
      AND LOWER(f.tipo) NOT LIKE '%grupo%'
);

-- 2. Resetear resultados de partidos KO (mantener equipos asignados)
UPDATE partido
SET
    goles_local           = NULL,
    goles_visitante       = NULL,
    estado                = 'programado',
    penales_local         = NULL,
    penales_visitante     = NULL,
    equipo_clasificado_id = NULL,
    amarillas             = NULL,
    rojas                 = NULL,
    local_amarillas       = NULL,
    visitante_amarillas   = NULL,
    local_rojas           = NULL,
    visitante_rojas       = NULL,
    decisiones_var        = NULL,
    penales_partido       = NULL,
    minuto_primer_gol     = NULL,
    minuto_actual         = NULL,
    datos_confirmados     = FALSE,
    api_fixture_id        = api_fixture_id   -- preservar mapeo API
WHERE id IN (
    SELECT p.id FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2
      AND LOWER(f.tipo) NOT LIKE '%grupo%'
);

-- 3. Eliminar puntaje_detalle de fases KO (grupos queda intacto al ser bloqueada)
DELETE FROM puntaje_detalle
WHERE partido_id IN (
    SELECT p.id FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2
      AND LOWER(f.tipo) NOT LIKE '%grupo%'
);

-- 4. Eliminar audit trail KO de apostador_clasificados (solo KO, no grupos)
DELETE FROM apostador_clasificados
WHERE torneo_id = 2
  AND fase_tipo != 'grupo';

-- 5. Desbloquear fases KO (por si quedaron bloqueadas de la simulacion)
UPDATE fase
SET bloqueada = FALSE
WHERE torneo_id = 2
  AND LOWER(tipo) NOT LIKE '%grupo%';

-- Verificacion final
SELECT
    f.nombre,
    f.tipo,
    f.bloqueada,
    COUNT(p.id)                    AS total_partidos,
    COUNT(p.goles_local)           AS con_goles,
    COUNT(p.equipo_clasificado_id) AS clasificados,
    COUNT(a.id)                    AS apuestas_ko
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id
LEFT JOIN apuesta a ON a.partido_id = p.id
WHERE f.torneo_id = 2
GROUP BY f.id, f.nombre, f.tipo, f.bloqueada
ORDER BY f.id;

COMMIT;

-- ============================================================
-- EJECUTAR via bat: doble click en run_reset_ko.bat
-- O directamente:
-- Get-Content "C:\proyecto FAST API\documentacion\reset_ko_resultados.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================
