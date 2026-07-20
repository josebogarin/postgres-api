-- ============================================================
-- Migración: Bonus por partido (minuto gol, amarillas, VAR)
-- Ejecutar en la BD: becbuc
-- Get-Content "...\migracion_bonus_partido.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

-- Predicciones de bonus en apuesta
ALTER TABLE apuesta
  ADD COLUMN IF NOT EXISTS pred_minuto_gol  SMALLINT DEFAULT NULL,  -- 1-90, null = no predicó
  ADD COLUMN IF NOT EXISTS pred_amarillas   SMALLINT DEFAULT NULL,  -- 0+,  null = no predicó
  ADD COLUMN IF NOT EXISTS pred_var         SMALLINT DEFAULT NULL,  -- 0+,  null = no predicó
  ADD COLUMN IF NOT EXISTS puntos_bonus     SMALLINT NOT NULL DEFAULT 0;

-- Resultados reales de bonus en partido
ALTER TABLE partido
  ADD COLUMN IF NOT EXISTS minuto_primer_gol  SMALLINT DEFAULT NULL,  -- null = sin goles / no cargado
  ADD COLUMN IF NOT EXISTS amarillas          SMALLINT DEFAULT NULL,  -- null = no cargado
  ADD COLUMN IF NOT EXISTS decisiones_var     SMALLINT DEFAULT NULL;  -- null = no cargado

-- Comentarios
COMMENT ON COLUMN apuesta.pred_minuto_gol  IS 'Predicción del minuto del primer gol (1-90). Por aproximación.';
COMMENT ON COLUMN apuesta.pred_amarillas   IS 'Predicción de cantidad de tarjetas amarillas en el partido.';
COMMENT ON COLUMN apuesta.pred_var         IS 'Predicción de decisiones VAR en el partido.';
COMMENT ON COLUMN apuesta.puntos_bonus     IS 'Puntos bonus acumulados: minuto gol + amarillas + VAR (máx 3 por partido).';

COMMENT ON COLUMN partido.minuto_primer_gol IS 'Minuto real del primer gol (null = sin goles o no cargado).';
COMMENT ON COLUMN partido.amarillas          IS 'Tarjetas amarillas totales del partido.';
COMMENT ON COLUMN partido.decisiones_var     IS 'Decisiones VAR del partido.';
