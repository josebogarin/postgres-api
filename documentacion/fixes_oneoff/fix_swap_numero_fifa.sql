-- ============================================================
-- FIX SWAP NUMERO FIFA — Adoptar numeración del Excel oficial
-- ============================================================
-- Los 5 pares tienen numero_fifa invertido respecto al Excel de la organización.
-- Este script intercambia los valores usando un número temporal para evitar
-- conflictos con la restricción UNIQUE.
--
-- Partidos NO cambian de lugar (partido_id intacto).
-- Predicciones NO se tocan (ya cargadas por equipos en sesión 36).
-- Puntajes NO requieren recálculo (vinculados a partido_id, no numero_fifa).
-- Solo cambia el DISPLAY NUMBER para que coincida con el Excel oficial.
--
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\fix_swap_numero_fifa.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

BEGIN;

-- Verificar estado actual (para debugging)
DO $$
DECLARE
  r RECORD;
BEGIN
  RAISE NOTICE 'Estado ANTES del fix:';
  FOR r IN
    SELECT p.numero_fifa, e1.nombre AS local, e2.nombre AS visitante
    FROM partido p
    JOIN equipo e1 ON e1.id = p.equipo_local_id
    JOIN equipo e2 ON e2.id = p.equipo_visitante_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.numero_fifa IN (49,50,55,56,61,62,65,66,67,68)
    ORDER BY p.numero_fifa
  LOOP
    RAISE NOTICE 'P%: % vs %', LPAD(r.numero_fifa::text, 3, '0'), r.local, r.visitante;
  END LOOP;
END$$;

-- ============================================================
-- PAR 1: P049 ↔ P050  (Morocco/Haiti ↔ Scotland/Brazil)
-- ============================================================
-- Paso a: Morocco/Haiti (actualmente 49) → temporal 1049
UPDATE partido SET numero_fifa = 1049
WHERE numero_fifa = 49
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE 'Morocco' LIMIT 1)
  AND equipo_visitante_id = (SELECT id FROM equipo WHERE nombre ILIKE 'Haiti' LIMIT 1);

-- Paso b: Scotland/Brazil (actualmente 50) → 49
UPDATE partido SET numero_fifa = 49
WHERE numero_fifa = 50
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE 'Scotland' LIMIT 1)
  AND equipo_visitante_id = (SELECT id FROM equipo WHERE nombre ILIKE 'Brazil' LIMIT 1);

-- Paso c: temporal 1049 → 50
UPDATE partido SET numero_fifa = 50 WHERE numero_fifa = 1049;

-- ============================================================
-- PAR 2: P055 ↔ P056  (Ecuador/Alemania ↔ Curaçao/Costa Marfil)
-- ============================================================
UPDATE partido SET numero_fifa = 1055
WHERE numero_fifa = 55
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Ecuador%' LIMIT 1)
  AND equipo_visitante_id IN (SELECT id FROM equipo WHERE nombre ILIKE '%Germany%' OR nombre ILIKE '%Alemania%' OR nombre ILIKE '%Deutschland%' LIMIT 1);

UPDATE partido SET numero_fifa = 55
WHERE numero_fifa = 56
  AND equipo_local_id IN (SELECT id FROM equipo WHERE nombre ILIKE '%Cura%' LIMIT 1);

UPDATE partido SET numero_fifa = 56 WHERE numero_fifa = 1055;

-- ============================================================
-- PAR 3: P061 ↔ P062  (Senegal/Iraq ↔ Norway/France)
-- ============================================================
UPDATE partido SET numero_fifa = 1061
WHERE numero_fifa = 61
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Senegal%' LIMIT 1)
  AND equipo_visitante_id = (SELECT id FROM equipo WHERE nombre ILIKE '%Iraq%' LIMIT 1);

UPDATE partido SET numero_fifa = 61
WHERE numero_fifa = 62
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Norway%' LIMIT 1)
  AND equipo_visitante_id = (SELECT id FROM equipo WHERE nombre ILIKE '%France%' LIMIT 1);

UPDATE partido SET numero_fifa = 62 WHERE numero_fifa = 1061;

-- ============================================================
-- PAR 4: P065 ↔ P066  (Uruguay/Spain ↔ Cape Verde/Saudi Arabia)
-- ============================================================
UPDATE partido SET numero_fifa = 1065
WHERE numero_fifa = 65
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Uruguay%' LIMIT 1)
  AND equipo_visitante_id IN (SELECT id FROM equipo WHERE nombre ILIKE '%Spain%' OR nombre ILIKE '%Espa%' LIMIT 1);

UPDATE partido SET numero_fifa = 65
WHERE numero_fifa = 66
  AND equipo_local_id IN (SELECT id FROM equipo WHERE nombre ILIKE '%Cape Verde%' OR nombre ILIKE '%Cabo Verde%' LIMIT 1);

UPDATE partido SET numero_fifa = 66 WHERE numero_fifa = 1065;

-- ============================================================
-- PAR 5: P067 ↔ P068  (Croatia/Ghana ↔ Panama/England)
-- ============================================================
UPDATE partido SET numero_fifa = 1067
WHERE numero_fifa = 67
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Croatia%' OR nombre ILIKE '%Croacia%' LIMIT 1)
  AND equipo_visitante_id = (SELECT id FROM equipo WHERE nombre ILIKE '%Ghana%' LIMIT 1);

UPDATE partido SET numero_fifa = 67
WHERE numero_fifa = 68
  AND equipo_local_id  = (SELECT id FROM equipo WHERE nombre ILIKE '%Panama%' LIMIT 1)
  AND equipo_visitante_id IN (SELECT id FROM equipo WHERE nombre ILIKE '%England%' OR nombre ILIKE '%Inglaterra%' LIMIT 1);

UPDATE partido SET numero_fifa = 68 WHERE numero_fifa = 1067;

-- ============================================================
-- Verificar resultado
-- ============================================================
DO $$
DECLARE
  r RECORD;
  pendientes INT;
BEGIN
  -- Verificar que no queden temporales
  SELECT COUNT(*) INTO pendientes FROM partido WHERE numero_fifa >= 1049 AND numero_fifa <= 1068;
  IF pendientes > 0 THEN
    RAISE EXCEPTION 'ERROR: quedaron % partidos con numero_fifa temporal — ROLLBACK', pendientes;
  END IF;

  RAISE NOTICE 'Estado DESPUÉS del fix:';
  FOR r IN
    SELECT p.numero_fifa, e1.nombre AS local, e2.nombre AS visitante
    FROM partido p
    JOIN equipo e1 ON e1.id = p.equipo_local_id
    JOIN equipo e2 ON e2.id = p.equipo_visitante_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.numero_fifa IN (49,50,55,56,61,62,65,66,67,68)
    ORDER BY p.numero_fifa
  LOOP
    RAISE NOTICE 'P%: % vs %', LPAD(r.numero_fifa::text, 3, '0'), r.local, r.visitante;
  END LOOP;
  RAISE NOTICE 'Fix aplicado correctamente.';
END$$;

COMMIT;
