-- Eliminar rol 'apostador' de jose (usuario admin, no apostador)
-- EJECUTAR: Get-Content "C:\proyecto FAST API\documentacion\fix_jose_rol.sql" | docker exec -i core-postgres psql -U app_user -d app_db

-- Ver roles actuales de jose
SELECT u.id, u.username, ro.name AS rol
FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles ro ON ro.id = ur.role_id
WHERE LOWER(u.username) = 'jose';

-- Eliminar rol apostador de jose
DELETE FROM user_roles
WHERE user_id = (SELECT id FROM users WHERE LOWER(username) = 'jose')
  AND role_id  = (SELECT id FROM roles WHERE name = 'apostador');

-- Confirmar resultado
SELECT u.id, u.username, ro.name AS rol
FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles ro ON ro.id = ur.role_id
WHERE LOWER(u.username) = 'jose';
