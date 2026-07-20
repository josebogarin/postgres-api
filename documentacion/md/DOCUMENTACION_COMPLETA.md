# 📚 DOCUMENTACIÓN COMPLETA - Backend RBAC + Multi-Tenancy

**Fecha:** 2026-05-21  
**Versión:** 1.0  
**Estado:** Production Ready  

---

## 📑 ÍNDICE

1. [Visión General](#visión-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Stack Tecnológico](#stack-tecnológico)
4. [Esquema de Base de Datos](#esquema-de-base-de-datos)
5. [Configuración e Instalación](#configuración-e-instalación)
6. [Explicación del Código](#explicación-del-código)
7. [Endpoints y Ejemplos](#endpoints-y-ejemplos)
8. [Flujos de Negocio](#flujos-de-negocio)
9. [Próximos Pasos](#próximos-pasos)
10. [Notas Importantes](#notas-importantes)

---

## VISIÓN GENERAL

### Objetivo
Construir un **backend API unificado** con:
- ✅ Autenticación por usuario + sistema (multi-tenancy)
- ✅ Control de acceso basado en roles (RBAC)
- ✅ Generación automática de CRUD dinámico
- ✅ Diccionario de metadatos configurable
- ✅ Soporte para múltiples sistemas independientes
- ✅ Auditoría y sincronización automática

### Premisas Arquitectónicas
1. **TODO en un único servidor unificado** (`main.py`)
2. **Multi-tenancy a nivel de base de datos** (cada sistema tiene su propia BD)
3. **Diccionario centralizado** en `app_db` para metadatos
4. **CRUD generado dinámicamente** basado en el diccionario
5. **Sin dependencias externas complejas** (solo PostgreSQL + Flask)

---

## ARQUITECTURA DEL SISTEMA

### 1. Diagrama de Capas

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Futuro)                    │
│              React / Vue / Angular + Tailwind           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────────┐
│              CAPA API - Flask (main.py)                 │
├──────────────────────────────────────────────────────────┤
│  ✓ Autenticación (Auth class)                           │
│  ✓ Rutas REST (endpoints)                               │
│  ✓ Validación de datos                                  │
│  ✓ Control de acceso                                    │
│  ✓ Sincronización (DictSync class)                      │
│  ✓ Scheduler (APScheduler)                              │
└──────────────────────┬──────────────────────────────────┘
                       │ psycopg2 (PostgreSQL)
┌──────────────────────▼──────────────────────────────────┐
│            CAPA DATOS - PostgreSQL 16 (Docker)          │
├──────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐ │
│  │  app_db (Administración Central)                    │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │  • users, roles, permissions (RBAC)                 │ │
│  │  • user_roles, role_permissions (relaciones)        │ │
│  │  • sistema (configuración de BDs)                   │ │
│  │  • diccionario (metadatos de campos)                │ │
│  │  • cabecera (pantallas principales)                 │ │
│  │  • detalle (sub-pantallas/pestañas)                 │ │
│  │  • audit_logs, password_reset_tokens                │ │
│  │  • Vistas: user_full_info, user_permissions_agg     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  ventas_db (Datos de Negocio - Ejemplo)            │ │
│  ├─────────────────────────────────────────────────────┤ │
│  │  • clientes                                          │ │
│  │  • facturas                                          │ │
│  │  • items_factura                                     │ │
│  │  • pagos_factura                                     │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌─────────────────────────────────────────────────────┐ │
│  │  rrhh_db, admin_db, etc (Futuras)                   │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 2. Flujo de Autenticación

```
Usuario intenta login
         ↓
POST /auth/login {username, password, sistema}
         ↓
Verificar que sistema existe en tabla "sistema"
         ↓
Buscar usuario en users (conectado a app_db)
         ↓
Verificar password con bcrypt
         ↓
Si OK: buscar roles y permisos del usuario
         ↓
Generar JWT con {user_id, roles, permissions, sistema}
         ↓
Retornar token al cliente
         ↓
Cliente incluye token en Authorization: Bearer {token}
         ↓
Acceso a CRUD automático con permisos verificados
```

### 3. Flujo de CRUD Automático

```
Cliente: GET /api/sistema_ventas/facturas?page=1
         ↓
Validar token JWT
         ↓
Buscar en diccionario campos visibles para "facturas"
         ↓
Conectar a BD del sistema (sistema_ventas)
         ↓
Ejecutar SELECT solo con columnas visibles
         ↓
Retornar datos con paginación
         ↓
Respuesta JSON al cliente
```

### 4. Flujo de Sincronización

```
Iniciar servidor
         ↓
Ejecutar DictSync.sync() (sincronización inicial)
         ↓
Para cada sistema activo en tabla "sistema":
  ├─ Conectar a esa base de datos
  ├─ Leer schema (información_schema.columns)
  ├─ Para cada tabla.campo:
  │  ├─ Calcular propiedades (visible, readonly, tipo)
  │  └─ Insertar/actualizar en tabla diccionario
  └─ Completar
         ↓
Scheduler: repetir cada 1 hora automáticamente
         ↓
Endpoint manual: POST /admin/sync-dictionary
```

---

## STACK TECNOLÓGICO

| Componente | Tecnología | Versión |
|---|---|---|
| **Lenguaje Backend** | Python | 3.11+ |
| **Framework Web** | Flask | 2.3+ |
| **BD Principal** | PostgreSQL | 16 |
| **Contenedor BD** | Docker | latest |
| **ORM/Driver BD** | psycopg2 | 2.9+ |
| **Autenticación** | JWT (PyJWT) | 2.8+ |
| **Hash de Contraseñas** | bcrypt | 4.0+ |
| **Scheduler** | APScheduler | 3.10+ |
| **CORS** | Flask-CORS | 4.0+ |
| **Variables Entorno** | python-dotenv | 1.0+ |

### Dependencias (requirements.txt)
```
Flask==2.3.0
Flask-CORS==4.0.0
psycopg2-binary==2.9.0
PyJWT==2.8.0
bcrypt==4.0.0
APScheduler==3.10.0
python-dotenv==1.0.0
```

---

## ESQUEMA DE BASE DE DATOS

### app_db - Administración Central

#### Tabla: `users`
```sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**Propósito:** Almacena usuarios del sistema  
**Campos:**
- `id`: Identificador único
- `username`: Nombre de usuario (único)
- `email`: Correo electrónico (único)
- `password_hash`: Hash bcrypt de la contraseña
- `is_active`: Si el usuario está activo
- `created_at`: Fecha de creación

#### Tabla: `roles`
```sql
CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
);
```
**Propósito:** Define roles disponibles (admin, user, moderator, etc.)  
**Ejemplo de datos:**
```
id | name       | description
1  | admin      | Administrador total
2  | user       | Usuario estándar
3  | moderator  | Moderador de contenidos
```

#### Tabla: `permissions`
```sql
CREATE TABLE permissions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
);
```
**Propósito:** Define permisos granulares  
**Ejemplo de datos:**
```
id | name           | description
1  | user:read      | Leer usuarios
2  | user:write     | Crear/editar usuarios
3  | role:create    | Crear roles
4  | role:delete    | Eliminar roles
```

#### Tabla: `user_roles` (Relación N:N)
```sql
CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users(id),
    role_id BIGINT NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```
**Propósito:** Asignar múltiples roles a un usuario  
**Ejemplo:**
```
user_id | role_id
1       | 1          (admin tiene rol "admin")
2       | 2          (user1 tiene rol "user")
2       | 3          (user1 también tiene rol "moderator")
```

#### Tabla: `role_permissions` (Relación N:N)
```sql
CREATE TABLE role_permissions (
    role_id BIGINT NOT NULL REFERENCES roles(id),
    permission_id BIGINT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);
```
**Propósito:** Asignar múltiples permisos a un rol  
**Ejemplo:**
```
role_id | permission_id
1       | 1              (admin tiene permisos user:read, user:write, etc)
1       | 2
1       | 3
2       | 1              (user tiene solo user:read)
```

#### Tabla: `user_permissions` (Opcional - Permisos directos)
```sql
CREATE TABLE user_permissions (
    user_id BIGINT NOT NULL REFERENCES users(id),
    permission_id BIGINT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (user_id, permission_id)
);
```
**Propósito:** Asignar permisos directos sin pasar por roles (edge cases)

#### Tabla: `sistema`
```sql
CREATE TABLE sistema (
    id BIGSERIAL PRIMARY KEY,
    id_sistema VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    host_bd VARCHAR(255) NOT NULL,
    puerto_bd INTEGER DEFAULT 5432,
    nombre_bd VARCHAR(255) NOT NULL,
    usuario_bd VARCHAR(255) NOT NULL,
    contraseña_bd VARCHAR(255) NOT NULL,
    es_activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**Propósito:** Configuración de sistemas y sus bases de datos  
**Ejemplo:**
```sql
INSERT INTO sistema VALUES (
    1, 
    'sistema_ventas', 
    'Sistema de Ventas',
    'Gestión de facturas y pagos',
    'localhost', 5432, 'ventas_db', 'app_user', 'superpassword',
    true, NOW(), NOW()
);
```

#### Tabla: `diccionario`
```sql
CREATE TABLE diccionario (
    id BIGSERIAL PRIMARY KEY,
    id_sistema VARCHAR(100) NOT NULL REFERENCES sistema(id_sistema),
    campo VARCHAR(255) NOT NULL,  -- formato: tabla.columna
    alias VARCHAR(255),
    descripcion TEXT,
    tipo_dato VARCHAR(100),
    es_visible BOOLEAN DEFAULT true,
    es_solo_lectura BOOLEAN DEFAULT false,
    es_obligatorio BOOLEAN DEFAULT false,
    orden_campo INTEGER,
    decimales INTEGER DEFAULT 0,
    texto_ayuda TEXT,
    valor_defecto TEXT,
    multivalor TEXT,
    crear_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizar_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_sistema, campo)
);
```
**Propósito:** Metadatos de todos los campos de todas las tablas  
**Ejemplo:**
```sql
INSERT INTO diccionario VALUES (
    1,
    'sistema_ventas',
    'facturas.numero',
    'Número',
    'Número de factura',
    'varchar',
    true,
    false,
    true,
    10,
    0,
    'Ingrese número de factura único',
    'FAC-',
    NULL,
    NOW(),
    NOW()
);
```

#### Tabla: `cabecera`
```sql
CREATE TABLE cabecera (
    id BIGSERIAL PRIMARY KEY,
    id_sistema VARCHAR(100) NOT NULL REFERENCES sistema(id_sistema),
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    es_activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_sistema, nombre)
);
```
**Propósito:** Pantallas principales del sistema  
**Ejemplo:**
```
id | id_sistema     | nombre    | descripcion
1  | sistema_ventas | facturas  | Gestión de facturas
2  | sistema_ventas | clientes  | Base de clientes
```

#### Tabla: `detalle`
```sql
CREATE TABLE detalle (
    id BIGSERIAL PRIMARY KEY,
    cabecera_id BIGINT NOT NULL REFERENCES cabecera(id),
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    es_activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(cabecera_id, nombre)
);
```
**Propósito:** Sub-pantallas/pestañas de cada cabecera  
**Ejemplo:**
```
id | cabecera_id | nombre              | descripcion
1  | 1           | datos_basicos       | Datos de la factura
2  | 1           | items               | Items de la factura
3  | 1           | pagos               | Pagos aplicados
```

#### Tabla: `audit_logs`
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(255),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**Propósito:** Auditoría de acciones del sistema

#### Tabla: `password_reset_tokens`
```sql
CREATE TABLE password_reset_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
**Propósito:** Tokens para reset de contraseñas

#### Vistas
```sql
-- Vista detallada: fila por cada combinación usuario-rol-permiso
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

-- Vista agregada: arrays de roles y permisos por usuario
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
```

### ventas_db - Ejemplo de Sistema de Negocio

#### Tabla: `clientes`
```sql
CREATE TABLE clientes (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    telefono VARCHAR(20),
    estado_civil VARCHAR(50),
    ciudad VARCHAR(100),
    es_activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tabla: `facturas`
```sql
CREATE TABLE facturas (
    id BIGSERIAL PRIMARY KEY,
    numero VARCHAR(50) UNIQUE NOT NULL,
    cliente_id BIGINT NOT NULL REFERENCES clientes(id),
    fecha DATE NOT NULL,
    fecha_vencimiento DATE,
    monto_total NUMERIC(12, 2),
    estado VARCHAR(50) DEFAULT 'pendiente',
    descripcion TEXT,
    es_activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tabla: `items_factura`
```sql
CREATE TABLE items_factura (
    id BIGSERIAL PRIMARY KEY,
    factura_id BIGINT NOT NULL REFERENCES facturas(id),
    producto VARCHAR(255),
    cantidad NUMERIC(10, 2),
    precio_unitario NUMERIC(12, 2),
    descuento_porcentaje NUMERIC(5, 2) DEFAULT 0,
    subtotal NUMERIC(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Tabla: `pagos_factura`
```sql
CREATE TABLE pagos_factura (
    id BIGSERIAL PRIMARY KEY,
    factura_id BIGINT NOT NULL REFERENCES facturas(id),
    monto NUMERIC(12, 2),
    fecha_pago DATE,
    metodo_pago VARCHAR(50),
    referencia VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## CONFIGURACIÓN E INSTALACIÓN

### 1. Requisitos Previos
- Python 3.11+
- PostgreSQL 16
- Docker (para PostgreSQL)
- Windows PowerShell o CMD

### 2. Estructura de Carpetas
```
C:\proyecto FAST API/
├── src/
│   └── main.py              ← Servidor unificado
├── .env                      ← Variables de entorno
├── requirements.txt          ← Dependencias Python
├── DOCUMENTACION_COMPLETA.md ← Este archivo
└── venv/                     ← Virtual environment
```

### 3. Variables de Entorno (.env)
```bash
# Base de datos (app_db)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app_db
DB_USER=app_user
DB_PASSWORD=superpassword

# JWT
JWT_SECRET=W6DzxLKBm0lwQbPv4Y0XygceAEGahC6BE2kY1UdyVCzT2cJ8VynB-dHGFi2MKSd1

# Servidor
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
DEBUG=False
CORS_ORIGINS=*

# bcrypt
BCRYPT_ROUNDS=12
```

### 4. Instalación Paso a Paso

```powershell
# 1. Navegar a la carpeta del proyecto
cd C:\proyecto FAST API

# 2. Crear virtual environment
python -m venv venv

# 3. Activar virtual environment
venv\Scripts\Activate.ps1

# 4. Instalar dependencias
pip install flask flask-cors apscheduler pyjwt bcrypt psycopg2-binary --break-system-packages

# 5. Verificar PostgreSQL está corriendo
docker ps | findstr core-postgres

# 6. Ejecutar servidor
python src\main.py
```

### 5. Verificación de Instalación
```bash
# En otra terminal
curl http://localhost:5000/health

# Respuesta esperada:
# {"ok": true, "status": "running", "timestamp": "..."}
```

---

## EXPLICACIÓN DEL CÓDIGO

### Estructura de main.py

#### 1. Imports y Configuración Inicial
```python
import os, logging, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import psycopg2
from psycopg2.extras import RealDictCursor  # Retorna dicts en lugar de tuples
import jwt
import bcrypt

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET')
CORS(app)  # Permitir requests desde otros dominios
```

**Qué hace:**
- Importa todas las librerías necesarias
- Configura Flask como servidor web
- Habilita CORS para frontend futuro
- Configura logging para debug

#### 2. Conexión a Base de Datos
```python
ADMIN_DB = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def connect_admin():
    """Conecta a app_db"""
    return psycopg2.connect(**ADMIN_DB)

def connect_system(sistema_id):
    """Conecta a BD del sistema específico"""
    conn = connect_admin()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM sistema WHERE id_sistema = %s", [sistema_id])
    sistema = cur.fetchone()
    conn.close()
    
    if not sistema:
        return None
    
    # Conexión dinámica a la BD del sistema
    return psycopg2.connect(
        host=sistema['host_bd'],
        port=sistema['puerto_bd'],
        database=sistema['nombre_bd'],
        user=sistema['usuario_bd'],
        password=sistema['contraseña_bd']
    )
```

**Qué hace:**
- `connect_admin()`: Conexión fija a app_db
- `connect_system()`: Conexión dinámica basada en tabla "sistema"

#### 3. Clase Auth - Autenticación
```python
class Auth:
    @staticmethod
    def verify_password(password, hash_db):
        """Verifica contraseña contra hash bcrypt"""
        return bcrypt.checkpw(password.encode(), hash_db.encode())
    
    @staticmethod
    def login(username, password, sistema_id):
        """
        Autentica usuario:
        1. Verifica que el sistema existe
        2. Busca usuario en app_db
        3. Verifica contraseña con bcrypt
        4. Obtiene roles y permisos
        5. Genera JWT con 24h de expiración
        """
        conn = connect_admin()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar sistema
        cur.execute("SELECT * FROM sistema WHERE id_sistema = %s AND es_activo = true", 
                   [sistema_id])
        if not cur.fetchone():
            return None, "Sistema no válido"
        
        # Buscar usuario + roles/permisos (agregados en arrays)
        cur.execute("""
            SELECT u.*, 
                   array_agg(DISTINCT r.name) as roles,
                   array_agg(DISTINCT p.name) as permissions
            FROM users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN permissions p ON rp.permission_id = p.id
            WHERE u.username = %s AND u.is_active = true
            GROUP BY u.id
        """, [username])
        
        user = cur.fetchone()
        conn.close()
        
        # Validar usuario y contraseña
        if not user or not Auth.verify_password(password, user['password_hash']):
            return None, "Usuario o contraseña inválida"
        
        # Generar JWT
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'sistema': sistema_id,
            'roles': user['roles'] or [],
            'permissions': user['permissions'] or [],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return {'token': token, 'usuario': user['username'], ...}, None
```

**Qué hace:**
- Verifica credenciales contra hash bcrypt
- Obtiene roles y permisos del usuario
- Genera JWT con expiración de 24 horas

#### 4. Clase DictSync - Sincronización
```python
class DictSync:
    @staticmethod
    def sync():
        """
        Sincroniza diccionario con todas las BDs activas:
        1. Lee tabla "sistema" de app_db
        2. Para cada sistema:
           a. Conecta a su BD
           b. Lee schema (information_schema.columns)
           c. Inserta/actualiza registros en tabla diccionario
        """
        admin_conn = connect_admin()
        cur = admin_conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtener todos los sistemas activos
        cur.execute("SELECT * FROM sistema WHERE es_activo = true")
        sistemas = cur.fetchall()
        
        for sistema in sistemas:
            try:
                # Conectar a BD del sistema
                sistema_conn = connect_system(sistema['id_sistema'])
                if not sistema_conn:
                    continue
                
                # Leer schema de esa BD
                cur_sistema = sistema_conn.cursor(cursor_factory=RealDictCursor)
                cur_sistema.execute("""
                    SELECT table_name, column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    ORDER BY table_name, ordinal_position
                """)
                campos = cur_sistema.fetchall()
                
                # Para cada campo, insertar en diccionario
                for campo in campos:
                    tabla = campo['table_name']
                    columna = campo['column_name']
                    nombre_campo = f"{tabla}.{columna}"
                    
                    # Inferir propiedades
                    es_visible = columna not in ['created_at', 'updated_at', 'id']
                    es_solo_lectura = columna in ['id', 'created_at', 'updated_at']
                    
                    # Insertar o actualizar
                    cur_admin = admin_conn.cursor()
                    cur_admin.execute("""
                        INSERT INTO diccionario 
                        (id_sistema, campo, alias, tipo_dato, ...)
                        VALUES (...)
                        ON CONFLICT (id_sistema, campo) 
                        DO UPDATE SET actualizar_en = CURRENT_TIMESTAMP
                    """)
                
                admin_conn.commit()
                sistema_conn.close()
                
            except Exception as e:
                logger.error(f"Error en {sistema['id_sistema']}: {e}")
                admin_conn.rollback()
```

**Qué hace:**
- Lee schema de cada BD configurada
- Sincroniza metadatos en tabla diccionario
- Se ejecuta al iniciar + cada 1 hora automáticamente

#### 5. Rutas - Endpoints

**Autenticación:**
```python
@app.route('/auth/login', methods=['POST'])
def login():
    """
    POST /auth/login
    {
        "username": "admin",
        "password": "faute",
        "sistema": "sistema_ventas"
    }
    """
    data = request.json
    usuario, error = Auth.login(data['username'], data['password'], data['sistema'])
    
    if error:
        return jsonify({'ok': False, 'error': error}), 401
    
    return jsonify({'ok': True, 'data': usuario}), 200
```

**CRUD Automático:**
```python
@app.route('/api/<sistema>/<tabla>', methods=['GET'])
def api_list(sistema, tabla):
    """
    GET /api/sistema_ventas/facturas?page=1&limit=50
    
    Flujo:
    1. Conectar a BD del sistema
    2. Obtener campos visibles para esta tabla del diccionario
    3. SELECT solo columnas visibles
    4. Retornar con paginación
    """
    conn = connect_system(sistema)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Obtener campos visibles del diccionario
    campos = get_campos_visibles(sistema, tabla)
    columnas = ', '.join([c['campo'].split('.')[1] for c in campos])
    
    # Paginación
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    offset = (page - 1) * limit
    
    # Ejecutar query
    cur.execute(f"SELECT {columnas} FROM {tabla} LIMIT %s OFFSET %s", [limit, offset])
    datos = cur.fetchall()
    conn.close()
    
    return jsonify({
        'ok': True,
        'tabla': tabla,
        'page': page,
        'limit': limit,
        'total': len(datos),
        'datos': datos
    }), 200
```

#### 6. Scheduler - Ejecución Automática
```python
def start_scheduler():
    """
    Inicia scheduler de APScheduler:
    - Ejecuta DictSync.sync() cada 1 hora
    - Es non-blocking (corre en background)
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=DictSync.sync,
        trigger='interval',
        hours=1,
        id='sync_dict',
        name='Sync Diccionario',
        replace_existing=True
    )
    scheduler.start()
    logger.info("📅 Scheduler iniciado")

if __name__ == '__main__':
    start_scheduler()  # Iniciar scheduler
    DictSync.sync()    # Sincronización inicial
    app.run(host='0.0.0.0', port=5000, debug=False)
```

---

## ENDPOINTS Y EJEMPLOS

### Base URL
```
http://localhost:5000
```

### 1. AUTENTICACIÓN

#### GET /sistemas
Obtiene sistemas disponibles
```bash
curl http://localhost:5000/sistemas

Respuesta:
{
  "ok": true,
  "sistemas": [
    {
      "id_sistema": "sistema_ventas",
      "nombre": "Sistema de Ventas",
      "descripcion": "Gestión de facturas y clientes"
    }
  ]
}
```

#### POST /auth/login
Autentica usuario contra un sistema
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "faute",
    "sistema": "sistema_ventas"
  }'

Respuesta:
{
  "ok": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "usuario": "admin",
    "email": "admin@empresa.com",
    "sistema": "sistema_ventas",
    "roles": ["admin"],
    "permissions": ["user:read", "user:write", ...]
  }
}
```

### 2. ADMINISTRACIÓN

#### GET /admin/diccionario/{sistema}
Lista campos del diccionario
```bash
curl http://localhost:5000/admin/diccionario/sistema_ventas

Respuesta:
{
  "ok": true,
  "total": 24,
  "datos": [
    {
      "id": 1,
      "id_sistema": "sistema_ventas",
      "campo": "facturas.numero",
      "alias": "Número",
      "tipo_dato": "varchar",
      "es_visible": true,
      "es_solo_lectura": false,
      ...
    }
  ]
}
```

#### POST /admin/diccionario
Crea nuevo campo
```bash
curl -X POST http://localhost:5000/admin/diccionario \
  -H "Content-Type: application/json" \
  -d '{
    "id_sistema": "sistema_ventas",
    "campo": "facturas.numero_referencia",
    "alias": "Ref",
    "tipo_dato": "varchar",
    "es_visible": true,
    "es_obligatorio": true
  }'
```

#### POST /admin/sync-dictionary
Sincroniza diccionario manualmente
```bash
curl -X POST http://localhost:5000/admin/sync-dictionary

Respuesta:
{
  "ok": true,
  "mensaje": "Diccionario sincronizado"
}
```

### 3. CRUD AUTOMÁTICO

#### GET /api/{sistema}/{tabla}
Lista registros con paginación
```bash
curl "http://localhost:5000/api/sistema_ventas/facturas?page=1&limit=20"

Respuesta:
{
  "ok": true,
  "tabla": "facturas",
  "page": 1,
  "limit": 20,
  "total": 5,
  "datos": [
    {
      "id": 1,
      "numero": "FAC-001",
      "cliente_id": 1,
      "fecha": "2026-05-21",
      "monto_total": 1500.00,
      "estado": "pendiente"
    }
  ]
}
```

#### GET /api/{sistema}/{tabla}/{id}
Obtiene un registro
```bash
curl http://localhost:5000/api/sistema_ventas/facturas/1

Respuesta:
{
  "ok": true,
  "dato": {
    "id": 1,
    "numero": "FAC-001",
    ...
  }
}
```

#### POST /api/{sistema}/{tabla}
Crea nuevo registro
```bash
curl -X POST http://localhost:5000/api/sistema_ventas/facturas \
  -H "Content-Type: application/json" \
  -d '{
    "numero": "FAC-002",
    "cliente_id": 1,
    "fecha": "2026-05-21",
    "estado": "pendiente"
  }'

Respuesta:
{
  "ok": true,
  "id": 2,
  "mensaje": "facturas creado"
}
```

#### PUT /api/{sistema}/{tabla}/{id}
Actualiza registro
```bash
curl -X PUT http://localhost:5000/api/sistema_ventas/facturas/1 \
  -H "Content-Type: application/json" \
  -d '{
    "estado": "pagada",
    "monto_total": 1600.00
  }'

Respuesta:
{
  "ok": true,
  "mensaje": "facturas actualizado"
}
```

#### DELETE /api/{sistema}/{tabla}/{id}
Elimina registro
```bash
curl -X DELETE http://localhost:5000/api/sistema_ventas/facturas/1

Respuesta:
{
  "ok": true,
  "mensaje": "facturas eliminado"
}
```

### 4. INFO

#### GET /health
Verifica que servidor está activo
```bash
curl http://localhost:5000/health

Respuesta:
{
  "ok": true,
  "status": "running",
  "timestamp": "2026-05-21T15:30:00.000000"
}
```

#### GET /api/docs
Documentación HTML interactiva
```
http://localhost:5000/api/docs
```

---

## FLUJOS DE NEGOCIO

### Flujo 1: Login de Usuario

```
1. Usuario ingresa credenciales (username, password, sistema)
   ↓
2. Cliente envía POST /auth/login
   ↓
3. Backend verifica:
   - Sistema existe y está activo
   - Usuario existe y está activo
   - Contraseña coincide con hash bcrypt
   ↓
4. Si OK:
   - Obtiene roles del usuario desde tabla user_roles
   - Obtiene permisos asociados a esos roles desde role_permissions
   - Genera JWT con {user_id, roles, permissions, sistema, exp}
   ↓
5. Retorna JWT al cliente
   ↓
6. Cliente almacena JWT (localStorage/session)
   ↓
7. En cada request, cliente incluye: Authorization: Bearer {token}
```

### Flujo 2: Listar Datos de un Sistema

```
1. Cliente: GET /api/sistema_ventas/facturas?page=1&limit=20
   ↓
2. Backend recibe request
   ↓
3. Backend busca en diccionario:
   - Qué campos de tabla "facturas" son visibles
   - Qué campos son solo lectura
   ↓
4. Conecta a BD del sistema (ventas_db)
   ↓
5. Construye query SELECT dinámico:
   SELECT numero, cliente_id, fecha, monto_total, estado
   FROM facturas
   LIMIT 20 OFFSET 0
   ↓
6. Ejecuta query
   ↓
7. Retorna datos con metadata (page, limit, total)
```

### Flujo 3: Crear Registro

```
1. Cliente: POST /api/sistema_ventas/facturas
   {
     "numero": "FAC-003",
     "cliente_id": 2,
     "fecha": "2026-05-21",
     "estado": "pendiente"
   }
   ↓
2. Backend obtiene campos editables de diccionario
   ↓
3. Filtra campos read-only (no acepta cambios en id, created_at, updated_at)
   ↓
4. Construye INSERT dinámico:
   INSERT INTO facturas (numero, cliente_id, fecha, estado)
   VALUES ('FAC-003', 2, '2026-05-21', 'pendiente')
   RETURNING id
   ↓
5. Retorna ID del nuevo registro
```

### Flujo 4: Sincronización del Diccionario

```
Cada 1 hora (automático) o manual (POST /admin/sync-dictionary):
   ↓
1. Lee tabla "sistema" en app_db
   ↓
2. Para cada sistema activo:
   a. Conecta a su BD
   b. Lee schema usando information_schema.columns
   c. Para cada tabla.campo:
      - Verifica si existe en diccionario
      - Si no existe: INSERT
      - Si existe: UPDATE actualizar_en
   ↓
3. Completa sincronización
```

---

## PRÓXIMOS PASOS

### Fase 1: Datos de Prueba (Inmediato)

#### 1.1 Insertar Datos en app_db
```sql
-- Insertar sistema
INSERT INTO sistema (id_sistema, nombre, host_bd, nombre_bd, usuario_bd, contraseña_bd)
VALUES ('sistema_ventas', 'Sistema de Ventas', 'localhost', 'ventas_db', 'app_user', 'superpassword');

-- Verificar
SELECT * FROM sistema;
```

#### 1.2 Sincronizar Diccionario
```bash
curl -X POST http://localhost:5000/admin/sync-dictionary
```

#### 1.3 Insertar Datos de Negocio
```sql
-- En ventas_db
INSERT INTO clientes (nombre, email, telefono, estado_civil, ciudad)
VALUES ('Juan Pérez', 'juan@email.com', '555-1234', 'Soltero', 'Asunción');

INSERT INTO facturas (numero, cliente_id, fecha, estado)
VALUES ('FAC-001', 1, '2026-05-21', 'pendiente');
```

### Fase 2: Frontend Web (1-2 semanas)

#### 2.1 Crear Frontend React
```
tecnologias:
- React 18+
- Tailwind CSS
- Axios para HTTP
- React Router para navegación
- Context API para estado global
```

#### 2.2 Implementar Vistas
- **Login**: Seleccionar sistema → ingresar credenciales
- **Dashboard**: Sistemas disponibles del usuario
- **CRUD Automático**: 
  - Listar con paginación
  - Buscar y filtrar
  - Crear nuevo
  - Editar
  - Eliminar
  - Exportar a Excel

#### 2.3 Componentes React
```
src/
├── components/
│   ├── LoginForm.jsx
│   ├── DataTable.jsx
│   ├── FormEditor.jsx
│   ├── Navbar.jsx
│   └── ...
├── pages/
│   ├── LoginPage.jsx
│   ├── DashboardPage.jsx
│   ├── CrudPage.jsx
│   └── ...
├── services/
│   ├── api.js (llamadas HTTP)
│   ├── auth.js (gestión de tokens)
│   └── ...
└── context/
    └── AuthContext.jsx
```

### Fase 3: Funcionalidades Avanzadas (2-3 semanas)

#### 3.1 Búsqueda y Filtrado
```python
# En backend: agregar endpoint
GET /api/{sistema}/{tabla}/search?q=valor&campo=nombre
```

#### 3.2 Exportación de Datos
```python
# Excel, PDF, CSV
GET /api/{sistema}/{tabla}/export?format=excel
```

#### 3.3 Relaciones Entre Tablas
```python
# GET /api/sistema_ventas/facturas/1/items
# (obtener items de una factura específica)
```

#### 3.4 Validaciones Avanzadas
```python
# En diccionario: agregar campo "reglas_validacion"
# Validar en backend antes de insertar
```

#### 3.5 Historial de Cambios
```python
# Usar trigger SQL para registrar cambios en audit_logs
```

### Fase 4: Seguridad y Produción (1-2 semanas)

#### 4.1 HTTPS
- Certificado SSL/TLS
- Redireccionar HTTP → HTTPS

#### 4.2 Rate Limiting
```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/auth/login')
@limiter.limit("5 per minute")
def login():
    ...
```

#### 4.3 Validación de Entrada
```python
# Usar biblioteca como marshmallow o pydantic
# Validar tipos de datos, longitudes, patrones
```

#### 4.4 Logs Centralizados
```python
# ELK Stack (Elasticsearch, Logstash, Kibana)
# o Sentry para error tracking
```

#### 4.5 Testing
```
- Unit tests (pytest)
- Integration tests
- Test de seguridad (SQL injection, XSS, etc)
```

### Fase 5: Devops (1 semana)

#### 5.1 Containerización
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ .
CMD ["python", "main.py"]
```

#### 5.2 Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: superpassword
    ports:
      - "5432:5432"
  
  backend:
    build: .
    ports:
      - "5000:5000"
    depends_on:
      - postgres
```

#### 5.3 CI/CD
- GitHub Actions para tests automáticos
- Deploy automático a servidor

#### 5.4 Monitoreo
- Uptime monitoring
- Performance metrics
- Error tracking

### Roadmap Timeline

```
Semana 1: ✅ Backend RBAC + Multi-tenancy (HECHO)
Semana 2-3: Frontend React
Semana 4-5: Funcionalidades avanzadas
Semana 6-7: Seguridad y optimización
Semana 8: DevOps y deployment
```

---

## NOTAS IMPORTANTES

### 1. Seguridad

#### Contraseña de Prueba
La contraseña "faute" está hasheada con bcrypt. Para usuarios reales:
```python
import bcrypt
# Generar hash
hash = bcrypt.hashpw('mi_contraseña'.encode(), bcrypt.gensalt(12))
# Actualizar en BD
UPDATE users SET password_hash = '{hash}' WHERE username = 'admin'
```

#### JWT_SECRET
Cambiar en producción. Generar con:
```python
import secrets
print(secrets.token_urlsafe(32))  # 64+ caracteres
```

#### CORS
En producción, configurar solo dominios permitidos:
```python
CORS(app, origins=["https://misdominios.com"])
```

### 2. Performance

#### Índices de BD
Ya creados en schema:
```sql
CREATE INDEX idx_user_roles ON user_roles(user_id);
CREATE INDEX idx_sistema_id ON diccionario(id_sistema);
CREATE INDEX idx_facturas_cliente ON facturas(cliente_id);
```

#### Caché
Considerar redis para datos que no cambian frecuentemente:
- Configuración de sistemas
- Diccionario (se cachea después de sincronización)

### 3. Escalabilidad

#### Horizontal Scaling
El backend es stateless (sin sesiones locales), por lo que puede escalarse:
```yaml
services:
  backend1:
    ...
  backend2:
    ...
  load-balancer:
    ...
```

#### Base de Datos
Considerar replicación/clustering para BD en producción

### 4. Mantenimiento

#### Backup
```bash
docker exec core-postgres pg_dump -U app_user app_db > backup.sql
```

#### Restaurar
```bash
docker exec core-postgres psql -U app_user app_db < backup.sql
```

#### Logs
```bash
# Ver logs del servidor
tail -f server.log

# Ver logs del scheduler
docker logs core-postgres
```

---

## ARCHIVO DE CONTROL PARA LA PRÓXIMA SESIÓN

### Información Crítica a Recordar

**Credenciales**
```
Host: localhost
Puerto: 5432
Usuario BD: app_user
Contraseña: superpassword
BD Principal: app_db
BD Ejemplo: ventas_db
Contraseña de Prueba: faute
JWT_SECRET: W6DzxLKBm0lwQbPv4Y0XygceAEGahC6BE2kY1UdyVCzT2cJ8VynB-dHGFi2MKSd1
```

**Ubicaciones de Archivos**
```
Servidor: C:\proyecto FAST API\src\main.py
Documentación: C:\proyecto FAST API\DOCUMENTACION_COMPLETA.md
Variables Entorno: C:\proyecto FAST API\.env
```

**Comandos Rápidos**
```powershell
# Iniciar servidor
cd C:\proyecto FAST API
venv\Scripts\Activate.ps1
python src\main.py

# Verificar BD
docker exec core-postgres psql -U app_user -d app_db -c "\dt"

# Sincronizar diccionario
curl -X POST http://localhost:5000/admin/sync-dictionary
```

**Estado Actual**
- ✅ Backend completamente funcional
- ✅ Todos los endpoints operacionales
- ✅ Sincronización automática configurada
- ✅ RBAC + Multi-tenancy implementado
- ⏳ Frontend pendiente (Fase 2)

---

**Documento creado:** 2026-05-21  
**Última actualización:** 2026-05-21  
**Versión:** 1.0 - Documentación Inicial
