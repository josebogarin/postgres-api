# Proyecto: RBAC + Auth en PostgreSQL (Docker) — Brief para Claude

> **Objetivo**: que Claude entienda el contexto completo del proyecto (conceptos, estructura, DB, vistas, seed, Docker y próximos pasos) para generar código consistente y seguro.

---

## 1) Conceptualización (qué estamos construyendo)

Estamos construyendo la base de un sistema de autenticación/autorización con **RBAC** (Role-Based Access Control) sobre **PostgreSQL**.

- **Usuarios**: credenciales y estado.
- **Roles**: agrupación lógica de permisos (ej. `admin`, `user`).
- **Permisos**: acciones granulares (ej. `user:read`, `role:create`).
- **Relaciones**:
  - Un usuario puede tener **múltiples roles** (`user_roles`).
  - Un rol puede tener **múltiples permisos** (`role_permissions`).
  - (Opcional) permisos directos a usuario (`user_permissions`).
- **Auditoría**: tabla simple `audit_logs`.
- **Tokens**: tabla `password_reset_tokens`.

Para simplificar el backend y evitar JOINs repetitivos, usamos **vistas**:
- `user_full_info`: vista detallada (fila por combinación usuario–rol–permiso).
- `user_permissions_agg`: vista agregada (roles/permisos en arrays), ideal para endpoints tipo `/me` y para generar JWT.

---

## 2) Stack actual

- **DB**: PostgreSQL **16** en Docker
- **Contenedor**: `core-postgres` (imagen `postgres:16`)
- **Base de datos**: `app_db`
- **Usuario DB**: `app_user`
- **Nota importante**: el rol `postgres` NO existe en este contenedor (se inicializó con otro usuario), por eso al conectar con `-U postgres` daba `role "postgres" does not exist`.

> Nota: dentro del contenedor, conexiones vía `docker exec ... psql` pueden no pedir password (conexión local). Desde fuera (DBeaver/backend) sí aplica password según configuración.

---

## 3) Estructura de directorios del proyecto

Estructura sugerida (la que estamos usando o equivalente):

### Propósito de cada parte

- **init-db/01_schema.sql**
  - Crea todas las tablas y constraints (PK/FK/UNIQUE/CHECK)
  - Crea índices
  - Crea vistas (`user_full_info`, `user_permissions_agg`)

- **init-db/02_seed.sql**
  - Inserta permisos base
  - Inserta roles base
  - Asigna permisos a roles
  - Inserta usuarios iniciales
  - Asigna roles a usuarios

- **backend/**
  - API REST (Node.js + Express)
  - Conexión DB con `pg` (Pool)
  - Login con bcrypt + JWT (próximo paso)

---

## 4) Esquema de Base de Datos (resumen)

### Tablas principales

- `users`
  - `id BIGSERIAL PK`
  - `username UNIQUE`
  - `email UNIQUE`
  - `password_hash` (bcrypt)
  - `is_active`
  - `created_at`

- `roles`
  - `id BIGSERIAL PK`
  - `name UNIQUE`
  - `description`

- `permissions`
  - `id BIGSERIAL PK`
  - `name UNIQUE`
  - `description`

### Tablas puente

- `user_roles` (N:N)
  - PK compuesta `(user_id, role_id)`
  - FK a `users(id)` y `roles(id)`

- `role_permissions` (N:N)
  - PK compuesta `(role_id, permission_id)`
  - FK a `roles(id)` y `permissions(id)`

- `user_permissions` (opcional)
  - PK compuesta `(user_id, permission_id)`
  - FK a `users` y `permissions`

### Auxiliares

- `audit_logs` (registro de acciones)
- `password_reset_tokens`

---

## 5) Vistas (SQL exacto recomendado)

> Estas vistas viven en `01_schema.sql`.

### 5.1 `user_full_info` (detallada)

```sql
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



CREATE OR REPLACE VIEW user_permissions_agg AS
SELECT
    u.id,
    u.username,
    u.email,
    ARRAY_AGG(DISTINCT r.name) FILTER (WHERE r.name IS NOT NULL) AS roles,
    ARRAY_AGG(DISTINCT p.name) FILTER (WHERE p.name IS NOT NULL) AS permissions
FROM users u
LEFT JOIN user_roles ur ON u.id = ur.user_id
LEFT JOIN roles r ON ur.role_id = r.id
LEFT JOIN role_permissions rp ON r.id = rp.role_id
LEFT JOIN permissions p ON rp.permission_id = p.id
GROUP BY u.id, u.username, u.email;


Como los SQL están en init-db/, la forma estable en Windows fue:


# Copiar al contenedor
docker cp init-db/01_schema.sql core-postgres:/01_schema.sql
docker cp init-db/02_seed.sql   core-postgres:/02_seed.sql

# Ejecutar dentro
docker exec -it core-postgres psql -U app_user -d app_db -f /01_schema.sql
docker exec -it core-postgres psql -U app_user -d app_db -f /02_seed.sql

#Credenciales de acceso a la base de datos
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=faute
JWT_SECRET=CAMBIAR_EN_PROD
BCRYPT_ROUNDS=12


# como hashear contraseñas
const bcrypt = require('bcrypt');
(async () => {
  const hash = await bcrypt.hash('faute', 12);
  console.log(hash);
})();


#actualizar contraseñas de prueba con el hash calculado de la palabra faute
UPDATE users
SET password_hash = '<PEGAR_HASH_BCRYPT>'
WHERE username IN ('admin','user1');

9) Backend: endpoints esperados (para que Claude genere)
9.1 Health check

GET /health → { ok: true }

9.2 Login

POST /auth/login

input: { "username": "admin", "password": "faute" }
lógica:

SELECT * FROM users WHERE username=$1 AND is_active=true
bcrypt.compare(password, user.password_hash)
si OK: buscar roles/permisos:

SELECT * FROM user_permissions_agg WHERE id=$1


firmar JWT con { sub: user.id, roles, permissions }





9.3 Me

GET /me

requiere Authorization: Bearer <token>
devuelve user_permissions_agg del usuario autenticado



9.4 Middleware de autorización

helper requirePermission('user:read')
valida que permission esté en el claim del token


10) Guía de estilo para Claude (cómo generar el código)

Node.js + Express
pg con Pool y queries parametrizadas
dotenv para env
bcrypt para hashing
jsonwebtoken para JWT
Código simple, modular:

src/db/pool.js
src/auth/jwt.js
src/auth/middleware.js
src/routes/auth.js
src/routes/me.js
src/server.js




11) Queries útiles


Listar vistas:

\dv (psql)
SELECT table_name FROM information_schema.views WHERE table_schema='public';



Obtener usuario + roles/permisos agregados:
SELECT * FROM user_permissions_agg WHERE username='admin';


El contenedor core-postgres existe y está corriendo.
La DB app_db existe.
Los scripts ya se ejecutaron y las tablas aparecen.
Próximo paso recomendado: generar bcrypt hash de "faute", actualizar users.password_hash, implementar login seguro con bcrypt + JWT.


