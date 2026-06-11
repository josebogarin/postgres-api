-- Migración: penales_partido
-- Agrega penales durante el partido (M — no son tanda) a las tablas becbuc

ALTER TABLE partido
    ADD COLUMN IF NOT EXISTS penales_partido SMALLINT;

ALTER TABLE puntaje_detalle
    ADD COLUMN IF NOT EXISTS pred_penales_partido SMALLINT,
    ADD COLUMN IF NOT EXISTS real_penales_partido  SMALLINT,
    ADD COLUMN IF NOT EXISTS pts_penales_partido   SMALLINT DEFAULT 0;

-- apuesta.pred_penales_partido ya fue agregada en migracion_scoring_v2.sql
-- Si no existiera, descomentar:
-- ALTER TABLE apuesta ADD COLUMN IF NOT EXISTS pred_penales_partido SMALLINT;
