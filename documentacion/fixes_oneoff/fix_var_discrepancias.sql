-- ============================================================
-- FIX DISCREPANCIAS VAR (y otros campos) — Datos del Excel oficial
-- ============================================================
-- Actualiza amarillas, rojas, decisiones_var, penales_partido, minuto_primer_gol
-- para los 4 partidos con diferencias vs Excel de la organización.
--
-- Fuente: "40- RESULTADOS OFICIALES" del Excel 20260702-TBL CHECK PARA JOSE.xlsx
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\fix_var_discrepancias.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- Luego: POST /api/v1/bets/calcular-puntajes/2  (para recalcular J/K/L/M/N)
-- ============================================================

BEGIN;

-- Verificar estado actual
DO $$
DECLARE r RECORD;
BEGIN
  RAISE NOTICE 'Estado ANTES del fix:';
  FOR r IN
    SELECT p.numero_fifa,
           e1.nombre AS local, e2.nombre AS visitante,
           p.amarillas, p.rojas, p.decisiones_var, p.penales_partido, p.minuto_primer_gol
    FROM partido p
    JOIN equipo e1 ON e1.id = p.equipo_local_id
    JOIN equipo e2 ON e2.id = p.equipo_visitante_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.numero_fifa IN (25, 64, 70, 71)
    ORDER BY p.numero_fifa
  LOOP
    RAISE NOTICE 'P%: % vs % | amar=% rojas=% var=% pen=% min=%',
      LPAD(r.numero_fifa::text, 3, '0'), r.local, r.visitante,
      r.amarillas, r.rojas, r.decisiones_var, r.penales_partido, r.minuto_primer_gol;
  END LOOP;
END$$;

-- ============================================================
-- P025: Chequia 1-1 Sudafrica
-- Excel: amarillas=3, rojas=0, VAR=0, penales_juego=1, minuto_gol=6
-- ============================================================
UPDATE partido SET
  amarillas         = 3,
  rojas             = 0,
  decisiones_var    = 0,
  penales_partido   = 1,
  minuto_primer_gol = 6
WHERE numero_fifa = 25
  AND EXISTS (
    SELECT 1 FROM fase f WHERE f.id = fase_id AND f.torneo_id = 2
  );

-- ============================================================
-- P064: Nueva Zelanda 1-5 Belgica
-- Excel: amarillas=2, rojas=0, VAR=2, penales_juego=0, minuto_gol=28
-- ============================================================
UPDATE partido SET
  amarillas         = 2,
  rojas             = 0,
  decisiones_var    = 2,
  penales_partido   = 0,
  minuto_primer_gol = 28
WHERE numero_fifa = 64
  AND EXISTS (
    SELECT 1 FROM fase f WHERE f.id = fase_id AND f.torneo_id = 2
  );

-- ============================================================
-- P070: Jordania 1-3 Argentina
-- Excel: amarillas=3, rojas=0, VAR=0, penales_juego=1, minuto_gol=19
-- ============================================================
UPDATE partido SET
  amarillas         = 3,
  rojas             = 0,
  decisiones_var    = 0,
  penales_partido   = 1,
  minuto_primer_gol = 19
WHERE numero_fifa = 70
  AND EXISTS (
    SELECT 1 FROM fase f WHERE f.id = fase_id AND f.torneo_id = 2
  );

-- ============================================================
-- P071: Colombia 0-0 Portugal
-- Excel: amarillas=1, rojas=0, VAR=2, penales_juego=0, minuto_gol=NULL (0-0 sin goles)
-- ============================================================
UPDATE partido SET
  amarillas         = 1,
  rojas             = 0,
  decisiones_var    = 2,
  penales_partido   = 0,
  minuto_primer_gol = NULL
WHERE numero_fifa = 71
  AND EXISTS (
    SELECT 1 FROM fase f WHERE f.id = fase_id AND f.torneo_id = 2
  );

-- Verificar resultado
DO $$
DECLARE r RECORD;
BEGIN
  RAISE NOTICE 'Estado DESPUÉS del fix:';
  FOR r IN
    SELECT p.numero_fifa,
           e1.nombre AS local, e2.nombre AS visitante,
           p.amarillas, p.rojas, p.decisiones_var, p.penales_partido, p.minuto_primer_gol
    FROM partido p
    JOIN equipo e1 ON e1.id = p.equipo_local_id
    JOIN equipo e2 ON e2.id = p.equipo_visitante_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2 AND p.numero_fifa IN (25, 64, 70, 71)
    ORDER BY p.numero_fifa
  LOOP
    RAISE NOTICE 'P%: % vs % | amar=% rojas=% var=% pen=% min=%',
      LPAD(r.numero_fifa::text, 3, '0'), r.local, r.visitante,
      r.amarillas, r.rojas, r.decisiones_var, r.penales_partido, r.minuto_primer_gol;
  END LOOP;
  RAISE NOTICE 'Fix aplicado. Recalcular puntajes: POST /api/v1/bets/calcular-puntajes/2';
END$$;

COMMIT;
