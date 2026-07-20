# 🚀 SKILL - Backend FastAPI del Proyecto

## Descripción

Este es el **backend oficial** para todo desarrollo de aplicaciones en el proyecto. Proporciona una API REST robusta con autenticación JWT, gestión de usuarios, aplicaciones, roles y auditoría centralizada.

**IMPORTANTE:** Siempre utiliza este backend para nuevos desarrollos. No crear backends alternativos.

---

## 📍 Ubicación

```
C:\proyecto FAST API\backend\
```

---

## 🚀 Cómo Ejecutar

### Terminal 1 - Inicia el Backend

```powershell
cd "C:\proyecto FAST API\backend"
pip install -r requirements.txt  # Solo primera vez
python -m uvicorn app.main:app --reload --port 8000
```

Verás:
```
Uvicorn running on http://127.0.0.1:8000
```

### Acceder a la Documentación API

```
http://localhost:8000/docs
```

Aquí puedes ver todos los endpoints disponibles y probarlos.

---

## 🔐 Credenciales de Desarrollo

```
Email:       admin@example.com
Contraseña:  changeme123
```

---

## 📚 Endpoints Principales

### Autenticación
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refrescar token
- `GET /api/v1/auth/me` - Obtener usuario actual

### Aplicaciones
- `GET /api/v1/applications` - Listar aplicaciones
- `POST /api/v1/applications` - Crear aplicación
- `GET /api/v1/applications/{id}` - Obtener detalle
- `PATCH /api/v1/applications/{id}` - Actualizar
- `DELETE /api/v1/applications/{id}` - Eliminar

### Usuarios
- `GET /api/v1/users` - Listar usuarios
- `POST /api/v1/users` - Crear usuario
- `GET /api/v1/users/{id}` - Obtener detalle
- `PATCH /api/v1/users/{id}` - Actualizar
- `DELETE /api/v1/users/{id}` - Eliminar

### Roles
- `GET /api/v1/roles` - Listar roles
- `POST /api/v1/roles` - Crear rol

### Auditoría
- `GET /api/v1/audit-logs` - Ver logs de auditoría

### Health
- `GET /api/v1/health` - Estado de la API

---

## 📦 Dependencias Principales

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.35
asyncpg>=0.29.0
pydantic>=2.9.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
```

---

## 🗄️ Base de Datos

### Sistema Principal
```
PostgreSQL 16
Host: localhost:5432
Database: users_db
Usuario: app_user
```

### Migraciones

Ver cambios en BD:
```powershell
cd backend
alembic current
alembic history
```

Crear nueva migración:
```powershell
alembic revision --autogenerate -m "descripción"
alembic upgrade head
```

---

## 🔑 JWT Tokens

### Access Token
- **Duración:** 30 minutos
- **Tipo:** HS256
- **Header:** `Authorization: Bearer <token>`

### Refresh Token
- **Duración:** 7 días
- **Uso:** Para obtener nuevo access token

```python
# Ejemplo de refresh
POST /api/v1/auth/refresh
{
  "refresh_token": "eyJ0eXAi..."
}
```

---

## 👥 Modelos de Datos

### User
```json
{
  "id": "uuid",
  "email": "string",
  "full_name": "string",
  "hashed_password": "string",
  "is_active": boolean,
  "is_superuser": boolean,
  "is_verified": boolean,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Application
```json
{
  "id": "uuid",
  "slug": "string",
  "name": "string",
  "description": "string",
  "db_url": "string",
  "is_active": boolean,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Role
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string"
}
```

---

## 🛠️ Flujo de Desarrollo

### Para Crear un Nueva Funcionalidad

1. **Definir modelo** en `app/models/`
2. **Crear schema** en `app/schemas/` (Pydantic)
3. **Implementar CRUD** en `app/crud/`
4. **Crear endpoint** en `app/api/v1/endpoints/`
5. **Registrar en router** en `app/api/v1/router.py`
6. **Crear migración** con Alembic
7. **Documentar en swagger** con docstrings

### Ejemplo

```python
# models/mi_modelo.py
from app.models.base import Base, UUIDMixin, TimestampMixin

class MiModelo(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "mi_modelo"
    
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(Text)

# schemas/mi_modelo.py
from pydantic import BaseModel

class MiModeloCreate(BaseModel):
    nombre: str
    descripcion: str | None = None

class MiModeloResponse(MiModeloCreate):
    id: str
    created_at: datetime

# crud/mi_modelo.py
from app.crud.base import CRUDBase
from app.models.mi_modelo import MiModelo

class CRUDMiModelo(CRUDBase[MiModelo, MiModeloCreate, MiModeloCreate]):
    pass

# api/v1/endpoints/mi_modelo.py
from fastapi import APIRouter
from app.api.deps import CurrentUser, DBSession

router = APIRouter()

@router.get("/", response_model=list[MiModeloResponse])
async def list_mi_modelo(db: DBSession):
    return await crud.mi_modelo.get_multi(db)
```

---

## 🔒 Seguridad

### Implementado
✅ JWT tokens seguros  
✅ Contraseñas hasheadas con bcrypt  
✅ CORS configurado  
✅ Auditoría de todas las acciones  
✅ Validación con Pydantic  
✅ Rate limiting (opcional)  
✅ HTTPS recomendado en producción  

### Headers de Seguridad
```python
# En app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Testing

### Smoke Tests
```powershell
cd backend
.\test_api.ps1
```

### Pytest
```powershell
pytest tests/ -v
```

---

## 🚨 Errores Comunes

### Error: "Module not found"
```
pip install -r requirements.txt
```

### Error: "Connection refused"
```
# Verificar PostgreSQL está corriendo
# Revisar DATABASE_URL en .env
```

### Error: "Token expired"
```
# Usar refresh_token para obtener nuevo access_token
POST /api/v1/auth/refresh
```

---

## 📝 Logs

### Ubicación
```
backend/logs/
```

### Nivel de Log
```python
# En .env
LOG_LEVEL=INFO
LOG_FORMAT=json  # o "console"
```

---

## 🔄 CI/CD

### Checks Automáticos
- Linting con ESLint (si aplica)
- Type checking con mypy
- Tests con pytest
- Coverage > 80%

---

## 📞 Soporte

### Ver documentación de la API
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

### Debugging
```python
# Ver logs en tiempo real
python -m uvicorn app.main:app --reload --log-level debug
```

---

## ✅ Checklist para Nuevo Desarrollo

- [ ] Backend FastAPI corriendo en puerto 8000
- [ ] Credenciales correctas (admin@example.com / changeme123)
- [ ] Acceso a documentación: http://localhost:8000/docs
- [ ] Frontend (Flask o Next.js) conectado correctamente
- [ ] Tokens JWT se están pasando en headers
- [ ] Auditoría registra las acciones
- [ ] Validaciones funcionan
- [ ] Tests pasan

---

## 🎯 Reglas Importantes

1. **SIEMPRE usar este backend** para nuevos desarrollos
2. **NO crear backends alternativos** sin justificación
3. **Mantener documentación actualizada**
4. **Validar en backend** (nunca confiar solo en frontend)
5. **Usar migraciones** para cambios en BD
6. **Registrar auditoría** para todas las acciones críticas
7. **Respetar JWT tokens** y expiración
8. **Documentar endpoints** con docstrings y ejemplos

---

## 📈 Próximos Pasos

1. Agregar más endpoints según requieras
2. Crear migraciones para nuevas tablas
3. Implementar webhooks si es necesario
4. Agregar caché (Redis) si el rendimiento lo requiere
5. Escalar horizontalmente con load balancer

---

**Última actualización:** Mayo 2026  
**Versión:** 1.0  
**Estado:** ✅ Producción-Ready
