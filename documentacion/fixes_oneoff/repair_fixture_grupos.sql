-- ============================================================
-- Reparación: reasignar partidos mal asignados a "Group Stage - 3"
-- al grupo correcto de cada equipo.
--
-- Ejecutar en: becbuc
-- Comando PowerShell:
--   Get-Content "C:\proyecto FAST API\documentacion\repair_fixture_grupos.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- 1. Ver estado ANTES
SELECT f.nombre, COUNT(p.id) AS partidos
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = 2
WHERE f.torneo_id = 2
GROUP BY f.id, f.nombre
ORDER BY f.nombre;

-- 2. Reasignar los 24 partidos de "Group Stage - 3" (fase id=31)
--    al Grupo correcto buscando via participacion de cada equipo
UPDATE partido p
SET fase_id = (
    SELECT pa.fase_id
    FROM participacion pa
    JOIN fase f ON f.id = pa.fase_id
    WHERE pa.equipo_id IN (p.equipo_local_id, p.equipo_visitante_id)
      AND f.torneo_id = 2
      AND f.nombre LIKE 'Grupo %'
    LIMIT 1
)
WHERE p.fase_id = 31
  AND p.torneo_id = 2;

-- 3. Confirmar cuántos se actualizaron
-- (debería ser 24)
SELECT 'partidos reasignados: ' || COUNT(*) FROM partido WHERE torneo_id = 2 AND fase_id != 31;

-- 4. Eliminar fases vacías / espurias del torneo 2
--    "Group Stage - 3" (id=31) y "Ranking of third-placed teams" (id=19)
DELETE FROM fase
WHERE torneo_id = 2
  AND nombre NOT LIKE 'Grupo %'
  AND tipo IN ('grupo', 'otro')
  AND NOT EXISTS (SELECT 1 FROM partido WHERE fase_id = fase.id);

-- 5. Ver estado DESPUÉS — todos los grupos deben tener 6 partidos
SELECT f.nombre, COUNT(p.id) AS partidos
FROM fase f
LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = 2
WHERE f.torneo_id = 2
GROUP BY f.id, f.nombre
ORDER BY f.nombre;

COMMIT;
