-- ============================================================
-- fix_pts_penales_partido.sql
-- Agrega pts_penales_partido a puntaje_detalle si no existe.
-- (Fue habilitado en sesion 20 pero faltó en migracion_scoring_v2.sql)
--
-- EJECUTAR:
--   Get-Content "C:\proyecto FAST API\documentacion\fix_pts_penales_partido.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
-- ============================================================

ALTER TABLE puntaje_detalle
    ADD COLUMN IF NOT EXISTS pts_penales_partido INT DEFAULT 0;

-- Verificacion
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'puntaje_detalle'
  AND column_name = 'pts_penales_partido';

SELECT COUNT(*) AS filas_puntaje_detalle FROM puntaje_detalle;
