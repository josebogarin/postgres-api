-- ============================================================
-- Migración: módulo apostador
-- Ejecutar: Get-Content "C:\proyecto FAST API\documentacion\migracion_apostador.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

-- 1. Agregar campos de apostador a users
ALTER TABLE users ADD COLUMN IF NOT EXISTS nombre_completo varchar(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS ci varchar(20) UNIQUE;

-- 2. Rol apostador
INSERT INTO roles (name, description)
VALUES ('apostador', 'Apostador — acceso solo a la interfaz de apuestas')
ON CONFLICT (name) DO NOTHING;

-- 3. Los apostadores se crean desde usuarios.html del backend (no se pre-insertan aquí).
--    Asignarles el rol 'apostador' desde la interfaz de gestión de usuarios.

-- 4. Tabla apuesta — se encuentra en la BD becbuc (migracion_becbuc_db.sql)
-- No crear aquí. La tabla apuesta vive en becbuc con apostador_id como FK lógica a app_db.users(id).
