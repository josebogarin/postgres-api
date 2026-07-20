-- ============================================================
-- Seed: Sistema app_db + Cabecera-Detalle para users y roles
-- Base interna de la plataforma (app_db)
-- Ejecutar con:
--   Get-Content "C:\proyecto FAST API\documentacion\seed_appdb_cabecera.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

-- ──────────────────────────────────────────────────────────
-- 1. Sistema para app_db (base interna)
--    nombre_bd = 'app_db' permite usar el endpoint admin sin
--    db_slug (el backend usa app_db por defecto cuando no
--    hay db_slug, pero al registrarlo se puede ver en el selector)
-- ──────────────────────────────────────────────────────────
INSERT INTO sistema (nombre, descripcion, host_bd, puerto_bd, nombre_bd, usuario_bd, "contraseña_bd", es_activo)
SELECT 'App DB', 'Base de datos interna de la plataforma', 'localhost', 5432, 'app_db', 'app_user', 'superpassword', true
WHERE NOT EXISTS (SELECT 1 FROM sistema WHERE nombre_bd = 'app_db');

-- ──────────────────────────────────────────────────────────
-- 2. Obtener IDs
-- ──────────────────────────────────────────────────────────
DO $$
DECLARE
  v_sistema_id  bigint;
  v_cab_users   bigint;
  v_cab_roles   bigint;
BEGIN

  SELECT id INTO v_sistema_id FROM sistema WHERE nombre_bd = 'app_db' LIMIT 1;

  IF v_sistema_id IS NULL THEN
    RAISE EXCEPTION 'No se encontró el sistema app_db. Revisá el INSERT anterior.';
  END IF;

  -- ── Cabecera: users ──────────────────────────────────────
  INSERT INTO cabecera (id_sistema, nombre, descripcion, es_activo)
  SELECT v_sistema_id, 'users', 'Usuarios de la plataforma', true
  WHERE NOT EXISTS (SELECT 1 FROM cabecera WHERE id_sistema = v_sistema_id AND nombre = 'users');

  SELECT id INTO v_cab_users FROM cabecera WHERE id_sistema = v_sistema_id AND nombre = 'users' LIMIT 1;

  -- Detalles de users
  INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
  SELECT v_cab_users, 'user_roles', 'Roles asignados al usuario', 'user_id', true
  WHERE NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cab_users AND nombre = 'user_roles');

  INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
  SELECT v_cab_users, 'user_permissions', 'Permisos directos del usuario', 'user_id', true
  WHERE NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cab_users AND nombre = 'user_permissions');

  INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
  SELECT v_cab_users, 'user_sistemas', 'Sistemas a los que tiene acceso', 'user_id', true
  WHERE NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cab_users AND nombre = 'user_sistemas');

  -- ── Cabecera: roles ──────────────────────────────────────
  INSERT INTO cabecera (id_sistema, nombre, descripcion, es_activo)
  SELECT v_sistema_id, 'roles', 'Roles del sistema', true
  WHERE NOT EXISTS (SELECT 1 FROM cabecera WHERE id_sistema = v_sistema_id AND nombre = 'roles');

  SELECT id INTO v_cab_roles FROM cabecera WHERE id_sistema = v_sistema_id AND nombre = 'roles' LIMIT 1;

  -- Detalles de roles
  INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
  SELECT v_cab_roles, 'user_roles', 'Usuarios que tienen este rol', 'role_id', true
  WHERE NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cab_roles AND nombre = 'user_roles');

  INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo)
  SELECT v_cab_roles, 'user_role_permissions', 'Permisos asignados a este rol', 'role_id', true
  WHERE NOT EXISTS (SELECT 1 FROM detalle WHERE id_cabecera = v_cab_roles AND nombre = 'user_role_permissions');

  RAISE NOTICE 'Seed completado. Sistema id=%, cabecera users id=%, cabecera roles id=%',
    v_sistema_id, v_cab_users, v_cab_roles;

END $$;

-- ──────────────────────────────────────────────────────────
-- 3. Verificación
-- ──────────────────────────────────────────────────────────
SELECT
  s.nombre AS sistema,
  s.nombre_bd AS db_slug,
  c.nombre AS cabecera,
  d.nombre AS detalle,
  d.campo_fk
FROM sistema s
JOIN cabecera c ON c.id_sistema = s.id
JOIN detalle  d ON d.id_cabecera = c.id
WHERE s.nombre_bd = 'app_db'
ORDER BY c.nombre, d.nombre;
