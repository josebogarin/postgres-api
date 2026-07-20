-- Migración: columna bloqueada en tabla fase
-- Control manual de bloqueo por fase (admin)
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_fase_bloqueada.sql" | docker exec -i core-postgres psql -U app_user -d becbuc

ALTER TABLE fase ADD COLUMN IF NOT EXISTS bloqueada BOOLEAN DEFAULT FALSE;

-- Verificar
SELECT id, nombre, tipo, orden, bloqueada FROM fase ORDER BY torneo_id, orden, nombre;
