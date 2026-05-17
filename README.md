# Postgres API

API REST centralizada de gestión de usuarios y permisos para aplicaciones multiplataforma.

## Stack

- **FastAPI** 0.115 + **SQLAlchemy** 2 async + **asyncpg**
- **Alembic** — migraciones de base de datos
- **PostgreSQL** 16 (Docker)
- **JWT** HS256 — access token (30 min) + refresh token (7 días)
- **bcrypt** 4.0.1 — hash de contraseñas

## Requisitos

- Python 3.11+
- Docker Desktop
- Git

## Setup en máquina nueva

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd postgres-docker
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` y completar al menos:
- `SECRET_KEY` — generar con `python -c "import secrets; print(secrets.token_hex(32))"`
- `FIRST_SUPERUSER_PASSWORD` — cambiar en producción

### 3. Opción A — Docker Compose (recomendado)

Levanta PostgreSQL + API + migraciones automáticas:

```bash
docker compose up --build
```

La API queda disponible en `http://localhost:8000`.  
Documentación interactiva: `http://localhost:8000/docs`

Para incluir pgAdmin (opcional):
```bash
docker compose --profile tools up --build
# pgAdmin en http://localhost:5050 (admin@admin.com / admin)
```

### 3. Opción B — Desarrollo local (sin Docker para la API)

Requiere PostgreSQL corriendo (puede ser el contenedor solo):

```bash
# Solo la base de datos en Docker
docker compose up db -d

# Instalar dependencias Python
pip install -r requirements.txt

# Ejecutar migraciones
alembic upgrade head

# Iniciar API con hot-reload
uvicorn app.main:app --reload --port 8000
```

## Estructura del proyecto

```
app/
├── api/v1/endpoints/   # Routers (auth, users, roles, applications)
├── core/               # Config, seguridad JWT, middleware de auditoría
├── models/             # SQLAlchemy ORM
├── schemas/            # Pydantic v2
├── services/           # Lógica de negocio
└── db/                 # Sesión async + multi-base de datos
alembic/                # Migraciones
tests/                  # pytest-asyncio
docker/                 # Dockerfile multi-stage
```

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | Login → access + refresh token |
| POST | `/api/v1/auth/refresh` | Renovar access token |
| GET  | `/api/v1/auth/me` | Perfil del usuario autenticado |
| GET  | `/api/v1/users/` | Listar usuarios |
| POST | `/api/v1/users/` | Crear usuario |
| PATCH | `/api/v1/users/{id}` | Actualizar / cambiar contraseña |

Ver documentación completa en `/docs` (Swagger) o `/redoc`.

## Tests

```bash
python -m pytest tests/ -v --cov=app
```

## Crear una nueva migración

```bash
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```
