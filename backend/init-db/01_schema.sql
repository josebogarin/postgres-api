-- =========================================
-- TABLA: users
-- =========================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS 'Usuarios del sistema';
COMMENT ON COLUMN users.id IS 'Identificador único del usuario';
COMMENT ON COLUMN users.username IS 'Nombre de usuario';
COMMENT ON COLUMN users.email IS 'Correo electrónico único';
COMMENT ON COLUMN users.password_hash IS 'Contraseña en hash';
COMMENT ON COLUMN users.is_active IS 'Indica si el usuario está activo';
COMMENT ON COLUMN users.created_at IS 'Fecha de creación del usuario';

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- =========================================
-- TABLA: roles
-- =========================================
CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

COMMENT ON TABLE roles IS 'Roles del sistema (admin, user, etc.)';
COMMENT ON COLUMN roles.id IS 'Identificador del rol';
COMMENT ON COLUMN roles.name IS 'Nombre del rol';
COMMENT ON COLUMN roles.description IS 'Descripción del rol';

-- =========================================
-- TABLA: permissions
-- =========================================
CREATE TABLE permissions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

COMMENT ON TABLE permissions IS 'Permisos específicos del sistema';
COMMENT ON COLUMN permissions.id IS 'Identificador del permiso';
COMMENT ON COLUMN permissions.name IS 'Nombre del permiso';
COMMENT ON COLUMN permissions.description IS 'Descripción del permiso';

-- =========================================
-- TABLA: user_roles (N:N)
-- =========================================
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
);

COMMENT ON TABLE user_roles IS 'Relación entre usuarios y roles';
COMMENT ON COLUMN user_roles.user_id IS 'ID del usuario';
COMMENT ON COLUMN user_roles.role_id IS 'ID del rol';

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);

-- =========================================
-- TABLA: role_permissions (N:N)
-- =========================================
CREATE TABLE role_permissions (
    role_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

COMMENT ON TABLE role_permissions IS 'Relación entre roles y permisos';
COMMENT ON COLUMN role_permissions.role_id IS 'ID del rol';
COMMENT ON COLUMN role_permissions.permission_id IS 'ID del permiso';

CREATE INDEX idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_perm ON role_permissions(permission_id);

-- =========================================
-- TABLA: user_permissions (override opcional)
-- =========================================
CREATE TABLE user_permissions (
    user_id BIGINT NOT NULL,
    permission_id BIGINT NOT NULL,
    PRIMARY KEY (user_id, permission_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);

COMMENT ON TABLE user_permissions IS 'Permisos directos del usuario';
COMMENT ON COLUMN user_permissions.user_id IS 'ID del usuario';
COMMENT ON COLUMN user_permissions.permission_id IS 'ID del permiso';

-- =========================================
-- TABLA: audit_logs
-- =========================================
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT,
    action VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE audit_logs IS 'Registro de actividad del sistema';
COMMENT ON COLUMN audit_logs.id IS 'ID del registro';
COMMENT ON COLUMN audit_logs.user_id IS 'Usuario que realizó la acción';
COMMENT ON COLUMN audit_logs.action IS 'Tipo de acción';
COMMENT ON COLUMN audit_logs.description IS 'Detalle de la acción';
COMMENT ON COLUMN audit_logs.created_at IS 'Fecha de la acción';

CREATE INDEX idx_audit_user ON audit_logs(user_id);

-- =========================================
-- TABLA: password_reset_tokens
-- =========================================
CREATE TABLE password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE password_reset_tokens IS 'Tokens para recuperación de contraseña';
COMMENT ON COLUMN password_reset_tokens.id IS 'ID del token';
COMMENT ON COLUMN password_reset_tokens.user_id IS 'Usuario asociado';
COMMENT ON COLUMN password_reset_tokens.token IS 'Token único';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Fecha de expiración';
COMMENT ON COLUMN password_reset_tokens.created_at IS 'Fecha de creación';

CREATE INDEX idx_tokens_user ON password_reset_tokens(user_id);


-- =========================================
-- VIEW: user_full_info
-- =========================================
CREATE OR REPLACE VIEW user_full_info AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    r.id AS role_id,
    r.name AS role,
    p.id AS permission_id,
    p.name AS permission
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id;

COMMENT ON VIEW user_full_info IS
'Vista detallada: una fila por combinación usuario-rol-permiso';