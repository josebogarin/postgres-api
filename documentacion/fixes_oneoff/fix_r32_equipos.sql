-- fix_r32_equipos.sql
-- Corrige los equipos visitantes en P86 y P87 del bracket R32.
--
-- ERROR ORIGINAL (fix_r32_oficial.py sesion 45):
--   P86 (Switzerland, Vancouver, Jul 2): visitante asignado = Senegal ← INCORRECTO
--   P87 (Belgium, Seattle, Jul 1):       visitante asignado = Algeria ← INCORRECTO
--
-- CORRECTO (verificado vs fuentes oficiales FIFA/NBC/CBS/SI jun-2026):
--   P86 = Switzerland vs Algeria  (FIFA Match 85, BC Place Vancouver)
--   P87 = Belgium vs Senegal      (FIFA Match 82, Lumen Field Seattle)
--
-- Senegal = Group I 3rd place, elegible para P87 (Belgium, Group G Winner, contra 3ro de A/E/H/I/J)
-- Algeria = Group J 3rd place, elegible para P86 (Switzerland, Group B Winner, contra 3ro de E/F/G/I/J)
--
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\fix_r32_equipos.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

BEGIN;

-- Verificar estado actual antes de modificar
SELECT p.numero_fifa,
       el.nombre AS local,
       ev.nombre AS visitante,
       p.estado
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.numero_fifa IN (86, 87)
ORDER BY p.numero_fifa;

-- Fix P86: Switzerland vs Algeria (cambiar visitante de Senegal a Algeria)
UPDATE partido
SET equipo_visitante_id = (
    SELECT id FROM equipo
    WHERE LOWER(nombre) IN ('algeria', 'algerie', 'algérie')
       OR LOWER(nombre_es) IN ('argelia', 'algeria')
    LIMIT 1
)
WHERE numero_fifa = 86
  AND estado != 'finalizado';  -- no tocar si ya se jugó

-- Fix P87: Belgium vs Senegal (cambiar visitante de Algeria a Senegal)
UPDATE partido
SET equipo_visitante_id = (
    SELECT id FROM equipo
    WHERE LOWER(nombre) = 'senegal'
       OR LOWER(nombre_es) = 'senegal'
    LIMIT 1
)
WHERE numero_fifa = 87
  AND estado != 'finalizado';  -- no tocar si ya se jugó

-- Verificar resultado después de modificar
SELECT p.numero_fifa,
       el.nombre AS local,
       ev.nombre AS visitante,
       p.estado
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.numero_fifa IN (86, 87)
ORDER BY p.numero_fifa;

COMMIT;
