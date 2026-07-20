# 🔍 Database Explorer API

**Nuevos Endpoints para Exploración Dinámica de PostgreSQL**

---

## 📍 Endpoints Disponibles

### **1. Listar Todas las Bases de Datos**

```
GET /api/v1/admin/db/databases
```

**Respuesta:**
```json
[
  {"name": "users_db"},
  {"name": "ventas_db"},
  {"name": "contabilidad_db"}
]
```

---

### **2. Listar Tablas y Vistas de una BD**

```
GET /api/v1/admin/db/databases/{database_name}/tables
```

**Parámetro:**
- `database_name`: Nombre de la base de datos (ej: `ventas_db`)

**Respuesta:**
```json
{
  "tables": [
    "clientes",
    "productos",
    "pedidos",
    "detalles_pedido",
    "facturas"
  ],
  "views": [
    "vw_resumen_ventas",
    "vw_top_productos"
  ]
}
```

---

### **3. Obtener Schema Completo de una Tabla**

```
GET /api/v1/admin/db/databases/{database_name}/tables/{table_name}/schema
```

**Parámetros:**
- `database_name`: Nombre de la BD (ej: `ventas_db`)
- `table_name`: Nombre de la tabla (ej: `clientes`)

**Respuesta:**
```json
{
  "table": "clientes",
  "columns": [
    {
      "name": "id",
      "type": "uuid",
      "nullable": false,
      "default": null,
      "max_length": null,
      "is_primary_key": true,
      "is_unique": false,
      "foreign_key": null,
      "description": "Identificador único del cliente",
      "is_active": true
    },
    {
      "name": "nombre",
      "type": "character varying",
      "nullable": false,
      "default": null,
      "max_length": 255,
      "is_primary_key": false,
      "is_unique": false,
      "foreign_key": null,
      "description": "Nombre completo del cliente",
      "is_active": true
    },
    {
      "name": "email",
      "type": "character varying",
      "nullable": false,
      "default": null,
      "max_length": 255,
      "is_primary_key": false,
      "is_unique": true,
      "foreign_key": null,
      "description": "Email del cliente",
      "is_active": true
    },
    {
      "name": "telefono",
      "type": "character varying",
      "nullable": true,
      "default": null,
      "max_length": 20,
      "is_primary_key": false,
      "is_unique": false,
      "foreign_key": null,
      "description": "Teléfono de contacto",
      "is_active": true
    }
  ],
  "indexes": ["clientes_pkey", "clientes_email_key"],
  "row_count": 145
}
```

---

### **4. Obtener Datos de una Tabla (CRUD Read)**

```
GET /api/v1/admin/db/databases/{database_name}/tables/{table_name}/rows
```

**Parámetros de Query:**
- `database_name`: Nombre de la BD
- `table_name`: Nombre de la tabla
- `skip`: Registros a saltar (default: 0)
- `limit`: Registros a retornar (default: 100, máx: 500)
- `search`: (Opcional) Búsqueda de texto libre

**Ejemplo:**
```
GET /api/v1/admin/db/databases/ventas_db/tables/clientes/rows?skip=0&limit=10&search=juan
```

**Respuesta:**
```json
{
  "table": "clientes",
  "total": 145,
  "skip": 0,
  "limit": 10,
  "columns": ["id", "nombre", "email", "telefono", "created_at"],
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "nombre": "Juan García",
      "email": "juan@example.com",
      "telefono": "555-1234",
      "created_at": "2026-05-20 10:30:00"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "nombre": "Juan Martínez",
      "email": "martinez@example.com",
      "telefono": "555-5678",
      "created_at": "2026-05-21 14:15:00"
    }
  ]
}
```

---

## 🔐 Autenticación

Todos los endpoints requieren:

```
Authorization: Bearer <access_token>
```

Y **solo superusers** pueden acceder.

---

## 💡 Casos de Uso

### **Caso 1: Dashboard - Selector de Aplicación**

```javascript
// 1. Obtener todas las bases de datos
GET /api/v1/admin/db/databases

// 2. Usuario selecciona "ventas_db"
// Frontend guarda: selectedDatabase = "ventas_db"
```

### **Caso 2: Dashboard - Selector de Tabla**

```javascript
// 1. Una vez seleccionada la BD
GET /api/v1/admin/db/databases/ventas_db/tables

// Respuesta: tables = ["clientes", "productos", "pedidos"]
// Frontend muestra estos en un listado
```

### **Caso 3: Dashboard - Ver Tabla**

```javascript
// 1. Usuario selecciona tabla "clientes"
GET /api/v1/admin/db/databases/ventas_db/tables/clientes/schema

// Respuesta: estructura completa de la tabla
// Frontend genera formulario dinámico basado en esto

// 2. Obtener los datos
GET /api/v1/admin/db/databases/ventas_db/tables/clientes/rows?skip=0&limit=100

// Respuesta: datos para llenar la tabla
```

### **Caso 4: Dashboard - Editar/Crear Registro**

```javascript
// Para editar o crear, necesitamos:
// 1. El schema (para validar tipos)
// 2. El diccionario (para descripciones y formato)

// Ya tenemos todo con:
GET /api/v1/admin/db/databases/ventas_db/tables/clientes/schema
```

---

## 📊 Flujo Completo de Usuario

```
1. Usuario abre dashboard
   ↓
2. Sistema obtiene: GET /databases
   → Muestra selector: [ventas ▼] [contabilidad ▼]
   ↓
3. Usuario selecciona "ventas"
   → Sistema obtiene: GET /databases/ventas_db/tables
   → Muestra listado: clientes, productos, pedidos...
   ↓
4. Usuario selecciona "clientes"
   → Sistema obtiene: GET /databases/ventas_db/tables/clientes/schema
   → Sistema obtiene: GET /databases/ventas_db/tables/clientes/rows
   → Genera formulario + tabla dinámicamente
   ↓
5. Usuario hace CRUD
   → Botones para editar/eliminar/crear
   → (Próxima fase: endpoints para CREATE, UPDATE, DELETE)
```

---

## 🛠️ Integración con Diccionario

Cada columna retorna:
- `description`: Del diccionario (si existe)
- `is_active`: Del diccionario (si existe)

Esto permite:
- Mostrar ayuda contextual en el formulario
- Ocultar columnas no activas
- Validar según el diccionario

---

## 🚀 Próxima Fase

Crear endpoints para:
- `POST /admin/db/databases/{db}/tables/{table}/rows` - Crear
- `PATCH /admin/db/databases/{db}/tables/{table}/rows/{pk}` - Editar
- `DELETE /admin/db/databases/{db}/tables/{table}/rows/{pk}` - Eliminar

Con validación automática basada en schema + diccionario.

---

## 📝 Notas Técnicas

- Los endpoints conectan directamente a PostgreSQL (no a través de la API de aplicaciones)
- Usan `information_schema` para obtener metadata
- Combinan con tabla `diccionario` para enriquecer datos
- Soportan búsqueda de texto libre
- Paginados para eficiencia

---

**Creado:** 2026-05-23  
**Status:** ✅ Fase 1 Completada  
**Próximo:** Frontend dinámico
