-- Visibilidad de torneos en el selector del Live (frontend nuevo).
-- El admin marca desde Portal -> Competiciones que campeonatos aparecen en el Live.
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\migraciones\migracion_mostrar_live.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE torneo ADD COLUMN IF NOT EXISTS mostrar_live BOOLEAN DEFAULT TRUE;
UPDATE torneo SET mostrar_live = TRUE WHERE mostrar_live IS NULL;
