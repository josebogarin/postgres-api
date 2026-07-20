-- =========================================
-- PERMISOS
-- =========================================
INSERT INTO permissions (name, description) VALUES
('user:create', 'Crear usuarios'),
('user:read', 'Leer usuarios'),
('user:update', 'Actualizar usuarios'),
('user:delete', 'Eliminar usuarios'),
('role:create', 'Crear roles'),
('role:read', 'Leer roles'),
('role:update', 'Actualizar roles'),
('role:delete', 'Eliminar roles'),
('permission:create', 'Crear permisos'),
('permission:read', 'Leer permisos'),
('permission:update', 'Actualizar permisos'),
('permission:delete', 'Eliminar permisos');

-- =========================================
-- ROLES
-- =========================================
INSERT INTO roles (name, description) VALUES
('admin', 'Acceso total al sistema'),
('user', 'Usuario básico');

-- =========================================
-- ASIGNAR PERMISOS A ROLES
-- =========================================

-- ADMIN: todos los permisos
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON true
WHERE r.name = 'admin';

-- USER: solo lectura básica
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
JOIN permissions p ON true
WHERE r.name = 'user'
AND p.name IN ('user:read');

-- =========================================
-- USUARIOS
-- =========================================

-- ⚠️ password_hash es solo ejemplo (usar bcrypt real)
INSERT INTO users (username, email, password_hash)
VALUES
('admin', 'admin@example.com', '$2b$10$examplehash'),
('user1', 'user1@example.com', '$2b$10$examplehash');

-- =========================================
-- ASIGNAR ROLES A USUARIOS
-- =========================================

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON true
WHERE u.username = 'admin'
AND r.name = 'admin';

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON true
WHERE u.username = 'user1'
AND r.name = 'user';

-- =========================================
-- VIEW: usuario + roles + permisos (DETALLADA)
-- =========================================
CREATE OR REPLACE VIEW user_full_info AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    r.name AS role,
    p.name AS permission
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id;

-- =========================================
-- VIEW: usuario optimizado para backend (AGREGADO)
-- =========================================
CREATE OR REPLACE VIEW user_permissions_agg AS
SELECT
    u.id,
    u.username,
    u.email,
    ARRAY_AGG(DISTINCT r.name) AS roles,
    ARRAY_AGG(DISTINCT p.name) AS permissions
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
GROUP BY u.id, u.username, u.email;

COMMENT ON VIEW user_full_info IS 'Vista detallada de usuario con roles y permisos';
COMMENT ON VIEW user_permissions_agg IS 'Vista optimizada para backend (roles y permisos agregados)';