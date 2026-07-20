# 🏗️ CRUD SYSTEM DESIGN - Backend Database

## 📋 Overview

Complete CRUD system designed for the FastAPI backend database including:
- **Diccionario (Data Dictionary)** - NEW table for schema metadata
- **Users** - Existing, improved CRUD
- **Applications** - Existing CRUD
- **Roles** - Existing CRUD + missing GET endpoint added
- **Permissions** - NEW CRUD system
- **Audit Logs** - Existing read-only CRUD

---

## 📊 Database Tables

### 1. Diccionario (Data Dictionary)

**Purpose:** Store metadata about database columns across all tables

**Fields:**
```
id                  UUID (PK)
tabla              varchar(100) - Table name [indexed]
columna            varchar(100) - Column name [indexed]
tipo_dato          varchar(50) - Data type (e.g., varchar, integer, text, boolean, uuid)
descripcion        text - Column description/documentation
es_nulo            boolean - Whether column allows NULL
es_llave_primaria  boolean - Is primary key
es_llave_foranea   boolean - Is foreign key
llave_foranea_tabla      varchar(100) - Referenced table (if FK)
llave_foranea_columna    varchar(100) - Referenced column (if FK)
es_indice          boolean - Has an index
es_unico           boolean - Has unique constraint
valor_por_defecto  varchar(255) - Default value
longitud_maxima    integer - Maximum length (for strings)
es_activo          boolean - Is active/in use
created_at         timestamp - Record creation time
updated_at         timestamp - Last update time
```

**Endpoints:**
```
GET    /api/v1/diccionario/                    - List all entries
GET    /api/v1/diccionario/activos             - List active only
GET    /api/v1/diccionario/tabla/{tabla}       - List columns for specific table
POST   /api/v1/diccionario/                    - Create entry
GET    /api/v1/diccionario/{id}                - Get single entry
PATCH  /api/v1/diccionario/{id}                - Update entry
DELETE /api/v1/diccionario/{id}                - Delete entry
```

---

### 2. Users

**Existing table - No changes needed**

**Endpoints:**
```
GET    /api/v1/users/                         - List all users
POST   /api/v1/users/                         - Create user (requires permission)
GET    /api/v1/users/{id}                     - Get user (self or superuser)
PATCH  /api/v1/users/{id}                     - Update user (self or superuser)
DELETE /api/v1/users/{id}                     - Delete user (requires permission)
POST   /api/v1/users/{id}/roles               - Assign role (superuser only)
DELETE /api/v1/users/{id}/roles/{role_id}     - Remove role (superuser only)
POST   /api/v1/users/{id}/applications        - Assign application (superuser only)
```

---

### 3. Applications

**Existing table - No changes needed**

**Endpoints:**
```
GET    /api/v1/applications/                 - List all applications
POST   /api/v1/applications/                 - Create application (superuser)
GET    /api/v1/applications/{id}             - Get application (superuser)
PATCH  /api/v1/applications/{id}             - Update application (superuser)
DELETE /api/v1/applications/{id}             - Delete application (superuser)
```

---

### 4. Roles

**Existing table - GET endpoint added**

**Endpoints:**
```
GET    /api/v1/roles/                        - List all roles
POST   /api/v1/roles/                        - Create role (superuser)
GET    /api/v1/roles/{id}                    - Get role (superuser) [NEW]
PATCH  /api/v1/roles/{id}                    - Update role (superuser)
DELETE /api/v1/roles/{id}                    - Delete role (superuser)
```

---

### 5. Permissions

**NEW - Complete CRUD system added**

**Fields:**
```
id            UUID (PK)
name          varchar(100) - Permission name [unique, indexed]
resource      varchar(100) - Resource name (e.g., "users", "applications")
action        varchar(50) - Action (e.g., "create", "read", "update", "delete")
description   varchar(255) - Permission description
created_at    timestamp - Record creation time
updated_at    timestamp - Last update time
```

**Endpoints:**
```
GET    /api/v1/permissions/                 - List all permissions
POST   /api/v1/permissions/                 - Create permission (superuser)
GET    /api/v1/permissions/{id}             - Get permission (superuser)
PATCH  /api/v1/permissions/{id}             - Update permission (superuser)
DELETE /api/v1/permissions/{id}             - Delete permission (superuser)
```

---

### 6. Audit Logs

**Existing table - Read-only CRUD**

**Endpoints:**
```
GET    /api/v1/audit-logs/                  - List audit logs (with filters)
```

---

## 📁 Files Created/Modified

### Created Files

**Models:**
- `C:\proyecto FAST API\backend\app\models\diccionario.py` - Diccionario model

**Schemas:**
- `C:\proyecto FAST API\backend\app\schemas\diccionario.py` - Diccionario schemas (Create, Update, Response)
- `C:\proyecto FAST API\backend\app\schemas\permission.py` - Permission schemas (Create, Update, Response)

**CRUD:**
- `C:\proyecto FAST API\backend\app\crud\diccionario.py` - Diccionario CRUD operations
- `C:\proyecto FAST API\backend\app\crud\permission.py` - Permission CRUD operations

**Endpoints:**
- `C:\proyecto FAST API\backend\app\api\v1\endpoints\diccionario.py` - Diccionario endpoints
- `C:\proyecto FAST API\backend\app\api\v1\endpoints\permissions.py` - Permission endpoints

**Migrations:**
- `C:\proyecto FAST API\backend\alembic\versions\2026_05_23_add_diccionario_table.py` - Migration for diccionario table

### Modified Files

**Router:**
- `C:\proyecto FAST API\backend\app\api\v1\router.py` - Added diccionario and permissions routers

**Endpoints:**
- `C:\proyecto FAST API\backend\app\api\v1\endpoints\roles.py` - Added missing GET /{role_id} endpoint

---

## 🛠️ Development Workflow

### Adding Dictionary Entries

```bash
# 1. Login first
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme123"}'

# 2. Create dictionary entry
curl -X POST "http://localhost:8000/api/v1/diccionario/" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "tabla": "users",
    "columna": "email",
    "tipo_dato": "varchar(255)",
    "descripcion": "User email address - unique identifier",
    "es_nulo": false,
    "es_llave_primaria": false,
    "es_llave_foranea": false,
    "es_indice": true,
    "es_unico": true,
    "es_activo": true
  }'

# 3. Get all columns for 'users' table
curl -X GET "http://localhost:8000/api/v1/diccionario/tabla/users" \
  -H "Authorization: Bearer <access_token>"

# 4. Get active entries only
curl -X GET "http://localhost:8000/api/v1/diccionario/activos" \
  -H "Authorization: Bearer <access_token>"

# 5. Update entry
curl -X PATCH "http://localhost:8000/api/v1/diccionario/{id}" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "descripcion": "Updated description"
  }'
```

---

## 🔐 Authentication & Authorization

All endpoints (except `/health`, `/auth/login`, `/auth/refresh`) require:

```
Authorization: Bearer <access_token>
```

**Permission Requirements:**
- **Diccionario endpoints** - Requires superuser
- **Permissions endpoints** - Requires superuser
- **Roles endpoints** - Requires superuser
- **Applications endpoints** - Requires superuser
- **Users endpoints** - Some require specific permissions (user:create, user:delete), others require superuser or self

---

## 📝 Standard Response Format

### List Response (Paginated)
```json
[
  {
    "id": "uuid",
    "tabla": "users",
    "columna": "email",
    "tipo_dato": "varchar(255)",
    "descripcion": "User email",
    "es_nulo": false,
    "es_llave_primaria": false,
    "es_llave_foranea": false,
    "llave_foranea_tabla": null,
    "llave_foranea_columna": null,
    "es_indice": true,
    "es_unico": true,
    "valor_por_defecto": null,
    "longitud_maxima": 255,
    "es_activo": true,
    "created_at": "2026-05-23T10:00:00+00:00",
    "updated_at": "2026-05-23T10:00:00+00:00"
  }
]
```

### Error Response
```json
{
  "detail": "Error message",
  "type": "error_type",
  "trace": "optional stack trace"
}
```

---

## 🚀 Implementation Steps

### Step 1: Apply Migration
```powershell
cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\alembic upgrade head
```

### Step 2: Restart Backend
```powershell
cd "C:\proyecto FAST API\backend"
.\.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Step 3: Verify Endpoints
Access Swagger UI:
```
http://localhost:8000/docs
```

You should see new endpoints:
- `/api/v1/diccionario/` - All diccionario operations
- `/api/v1/permissions/` - All permission operations
- `/api/v1/roles/{role_id}` - GET single role (new)

---

## 📚 API Documentation

Full OpenAPI documentation available at:
```
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

---

## ✅ Implementation Checklist

- [x] Diccionario model created
- [x] Diccionario schemas created (Create, Update, Response)
- [x] Diccionario CRUD operations implemented
- [x] Diccionario endpoints created (CRUD + table-specific queries)
- [x] Permissions schemas created
- [x] Permissions CRUD operations implemented
- [x] Permissions endpoints created
- [x] Roles GET single endpoint added
- [x] Router updated with new endpoints
- [x] Alembic migration created for diccionario table
- [x] CRUD system documentation created

---

## 🔄 CRUD Pattern Used

All CRUD implementations follow the same pattern:

```python
# Model (inherits UUIDMixin, TimestampMixin)
class MyModel(Base, UUIDMixin, TimestampMixin):
    pass

# Schema
class MyCreate(BaseSchema):
    pass

class MyUpdate(BaseSchema):
    pass

class MyResponse(BaseSchema, UUIDSchema, TimestampSchema):
    pass

# CRUD
class CRUDMyModel(CRUDBase[MyModel, MyCreate, MyUpdate]):
    # Custom query methods if needed
    pass

my_crud = CRUDMyModel(MyModel)

# Endpoints
@router.get("/")
async def list_items(db: DBSession, _: CurrentSuperuser):
    items, _ = await my_crud.get_multi(db, skip=skip, limit=limit)
    return items

@router.post("/", status_code=201)
async def create_item(body: MyCreate, db: DBSession, _: CurrentSuperuser):
    return await my_crud.create(db, obj_in=body)

@router.get("/{id}")
async def get_item(id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    item = await my_crud.get(db, id=id)
    if not item:
        raise NotFoundError("Item")
    return item

@router.patch("/{id}")
async def update_item(id: uuid.UUID, body: MyUpdate, db: DBSession, _: CurrentSuperuser):
    item = await my_crud.get(db, id=id)
    if not item:
        raise NotFoundError("Item")
    return await my_crud.update(db, db_obj=item, obj_in=body)

@router.delete("/{id}", status_code=204)
async def delete_item(id: uuid.UUID, db: DBSession, _: CurrentSuperuser):
    await my_crud.delete(db, id=id)
```

---

## 🎯 Next Steps

1. **Run migration** - Apply the Alembic migration to create the diccionario table
2. **Test endpoints** - Use Swagger UI or curl to test all endpoints
3. **Populate dictionary** - Add metadata entries for existing tables
4. **Web interface** - Create Flask templates to manage dictionary entries
5. **Frontend integration** - Create Next.js components for dictionary CRUD

---

**Created:** 2026-05-23  
**Status:** ✅ Ready for deployment  
**Backend Version:** 1.0  
**API Version:** v1
