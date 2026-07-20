-- Migración: columnas faltantes en apuesta (pred_rojas, pred_penales_partido, tanda)
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\backend\migracion_apuesta_cols_v2.sql" |
--   docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE apuesta
    ADD COLUMN IF NOT EXISTS pred_rojas                   SMALLINT,
    ADD COLUMN IF NOT EXISTS pred_penales_partido         SMALLINT,
    ADD COLUMN IF NOT EXISTS pred_penales_local_tanda     SMALLINT,
    ADD COLUMN IF NOT EXISTS pred_penales_visitante_tanda SMALLINT;

-- puntaje_detalle: columnas de scoring adicionales
ALTER TABLE puntaje_detalle
    ADD COLUMN IF NOT EXISTS pts_rojas              SMALLINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS pts_penales_tanda      SMALLINT DEFAULT 0;
