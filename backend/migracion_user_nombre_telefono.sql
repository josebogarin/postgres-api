-- Migración: agregar nombre, telefono y must_change_password a users (app_db)
-- Ejecutar: Get-Content "C:\proyecto FAST API\backend\migracion_user_nombre_telefono.sql" | docker exec -i core-postgres psql -U app_user -d app_db

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS nombre VARCHAR(100),
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(30),
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN users.nombre IS 'Nombre completo del apostador';
COMMENT ON COLUMN users.telefono IS 'Teléfono de contacto';
COMMENT ON COLUMN users.must_change_password IS 'True = primer login, el apostador debe setear su contraseña';
