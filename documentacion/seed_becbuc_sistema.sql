-- ============================================================
-- Seed: registrar sistema BECBUC en app_db
-- Ejecutar:
--   Get-Content "C:\proyecto FAST API\documentacion\seed_becbuc_sistema.sql" | docker exec -i core-postgres psql -U app_user -d app_db
-- ============================================================

INSERT INTO sistema (nombre, descripcion, host_bd, puerto_bd, nombre_bd, usuario_bd, contraseña_bd, es_activo)
VALUES (
    'BECBUC',
    'Sistema de torneos, fixture y apuestas deportivas',
    'localhost',
    5432,
    'becbuc',
    'app_user',
    'superpassword',
    true
)
ON CONFLICT DO NOTHING;

-- Asignar a todos los superadmin
INSERT INTO user_sistemas (user_id, sistema_id)
SELECT u.id, s.id
FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles r ON r.id = ur.role_id AND r.name = 'superadmin'
CROSS JOIN sistema s
WHERE s.nombre = 'BECBUC'
ON CONFLICT DO NOTHING;
