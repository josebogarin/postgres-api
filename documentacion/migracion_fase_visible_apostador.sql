-- Migración: agregar control de visibilidad por fase para app apostador
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_fase_visible_apostador.sql" | docker exec -i core-postgres psql -U app_user -d app_db

ALTER TABLE fase ADD COLUMN IF NOT EXISTS visible_apostador boolean NOT NULL DEFAULT true;

-- Por defecto todas las fases son visibles; el admin puede ocultarlas desde fixture.html
COMMENT ON COLUMN fase.visible_apostador IS 'Si true, la fase aparece en la app del apostador';
