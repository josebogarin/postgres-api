# FastAPI BECBUC Backend — Guía para Claude

Proyecto: **FastAPI + PostgreSQL + Docker**  
Backend corriendo en `http://localhost:8000`  
Arrancar: `cd "C:\proyecto FAST API\backend" && .\.venv\Scripts\uvicorn app.main:app --reload --port 8000`  
Credenciales dev: `admin` / `faute`  
Última actualización: 2026-06-10

---

## Bases de datos

| BD        | Propósito                                                     |
|-----------|---------------------------------------------------------------|
| `app_db`  | **Exclusiva del backend** — usuarios, roles, permisos, audit  |
| `becbuc`  | Base del sistema de torneos/apuestas                          |

Conexiones en `.env`:
```
DATABASE_URL=postgresql+asyncpg://app_user:superpassword@localhost:5432/app_db
DATABASE_BECBUC_URL=postgresql+asyncpg://app_user:superpassword@localhost:5432/becbuc
APIFOOTBALL_KEY=f13bee776659e2c20c715a81ecff2307
```

---

## ⚠️ REGLAS CRÍTICAS — SQLAlchemy 2.x async

### Relaciones ORM — cómo declararlas correctamente

```python
# ✅ CORRECTO — tipo explícito, sin back_populates en el lado "inverso"
roles: Mapped[list["Role"]] = relationship("Role", secondary=user_roles, lazy="raise")

# ❌ INCORRECTO — Mapped[list] sin tipo hace que SQLAlchemy 2.x resuelva scalar
roles: Mapped[list] = relationship("Role", secondary=user_roles, lazy="selectin")

# ❌ INCORRECTO — back_populates entre lazy="selectin" y lazy="noload" corrompe colección
# ❌ INCORRECTO — lazy="noload" no existe en SQLAlchemy 2.x (fue removido)
# ❌ INCORRECTO — doble carga: lazy="selectin" en modelo + selectinload() en CRUD
```

### Reglas para relaciones en async:

1. **Siempre usar tipos explícitos**: `Mapped[list["Role"]]` no `Mapped[list]`
2. **`lazy="raise"`** en el modelo para todas las relaciones colección — obliga a usar `selectinload()` explícito en el CRUD
3. **Cargar siempre con `selectinload()`** en el CRUD — nunca confiar en lazy load automático
4. **No usar `back_populates`** en relaciones many-to-many a menos que ambos lados tengan `lazy="raise"` o `lazy="select"` compatibles
5. **`lazy="noload"` NO EXISTE en SQLAlchemy 2.x** — usar `lazy="raise"` o `lazy="write_only"`
6. **No duplicar**: si el modelo tiene `lazy="selectin"` Y el CRUD usa `selectinload()`, hay doble carga que corrompe colecciones cuando los objetos ya están en la sesión

### Patrón correcto en CRUD:

```python
async def _get_with_relations(self, db: AsyncSession, stmt):
    result = await db.execute(
        stmt.options(
            selectinload(User.roles),
            selectinload(User.direct_permissions),
            selectinload(User.sistemas),
        )
    )
    return result.scalar_one_or_none()
```

### Serialización en endpoints — NO pasar objeto ORM a Pydantic directamente:

```python
# ✅ CORRECTO — construir dict explícito
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    roles_list = list(current_user.roles) if current_user.roles is not None else []
    return {
        "id": current_user.id,
        "username": current_user.username,
        "roles": [{"id": r.id, "name": r.name, "description": r.description} for r in roles_list],
        ...
    }

# ❌ INCORRECTO — from_attributes=True + InstrumentedList puede retornar scalar
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user  # PUEDE FALLAR
```

---

## Esquema `becbuc` — tablas del torneo (nombres en SINGULAR)

> ⚠️ Estas tablas son DIFERENTES a las del proyecto `C:\Proyectos\BECBUC` que usa nombres PLURALES.

| Tabla                 | Descripción                                              |
|-----------------------|----------------------------------------------------------|
| `competicion`         | Catálogo de competiciones (Mundial, Champions, etc.)     |
| `torneo`              | Edición anual de una competición                         |
| `equipo`              | Equipos/selecciones (tiene `api_team_id` UNIQUE)         |
| `fase`                | Fase del torneo (Grupo A, Ronda de 32, Final, etc.)      |
| `participacion`       | Standings por grupo (pj, pg, pe, pp, gf, gc, pts)       |
| `partido`             | Partidos con resultado y estado                          |
| `partido_estadistica` | Estadísticas por equipo por partido                      |
| `partido_evento`      | Eventos (goles, tarjetas, etc.)                          |
| `torneo_equipo`       | Equipos participantes en una edición                     |
| `jugador_estadistica` | Goleadores y asistencias                                 |
| `apuesta`             | Pronósticos de apostadores (FK lógica a app_db.users)   |

Schema completo: `documentacion/migracion_becbuc_db.sql`

### Tabla `equipo` — campos clave
- `api_team_id INTEGER UNIQUE` — ID de API-Football
- `nombre VARCHAR(100)` — nombre en inglés (de la API)
- `nombre_es VARCHAR(100)` — nombre en español
- `logo_url VARCHAR(500)` — URL del logo de API-Football
- `tipo VARCHAR(20)` — 'seleccion' | 'club'

### Tabla `fase` — campos clave
- `tipo VARCHAR(30)` — 'grupo' | 'ronda32' | 'ronda16' | 'cuartos' | 'semis' | 'tercer_puesto' | 'final'
- `orden INTEGER` — 10=grupos, 15=ronda32, 20=ronda16, 30=cuartos, 40=semis, 50=final
- `visible_apostador BOOLEAN DEFAULT true`
- UNIQUE(torneo_id, nombre)

### Tabla `partido` — estados válidos
`programado` | `en_juego` | `finalizado` | `suspendido` | `aplazado`

---

## Migraciones ejecutadas en `becbuc`

```powershell
# Ejecutar con:
Get-Content "C:\proyecto FAST API\documentacion\<archivo>.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
```

| Archivo | Estado |
|---------|--------|
| `migracion_becbuc_db.sql` | ✅ Ejecutada |
| `migracion_apostador.sql` | ✅ Ejecutada |
| `patch_torneos_v2.sql` | ✅ Ejecutada |
| `migracion_fase_visible_apostador.sql` | ✅ Ejecutada |

---

## Carga de fixture

### Fuente de datos
Los datos vienen de **API-Football** (api-sports.io) — **NO** de openfootball.

La clave API está en `.env`: `APIFOOTBALL_KEY=f13bee776659e2c20c715a81ecff2307` (100 req/día gratis).

### Flujo de carga (vía endpoints)
1. `POST /api/v1/torneo/sincronizar` → crea registros en `competicion` y `torneo`
2. `POST /api/v1/torneo/torneos/{id}/cargar` → descarga fixture completo de API-Football

### Seed manual de competición y torneo (alternativa sin API)
```sql
-- En becbuc:
INSERT INTO competicion (nombre, nombre_corto, tipo, formato_playoff, api_league_id, emoji)
VALUES ('Copa Mundial FIFA 2026', 'Mundial 2026', 'paises', 'partido_unico', 1, '🌍')
ON CONFLICT (api_league_id) DO NOTHING;

INSERT INTO torneo (competicion_id, anio, nombre, estado, api_season)
SELECT id, 2026, 'Copa Mundial FIFA 2026', 'en_curso', 2026
FROM competicion WHERE api_league_id = 1
ON CONFLICT (competicion_id, anio) DO NOTHING;
```

---

## Portal BECBUC — `http://localhost:8000/BECBUC-portal`

Archivo: `static/BECBUC-portal.html` (~1450 líneas, JS inline, dark mode Bet365)

### Endpoints que usa el portal Apuestas

| Endpoint | Implementado | Descripción |
|----------|-------------|-------------|
| `GET /api/v1/torneo/activas` | ✅ | Lista torneos activos |
| `GET /api/v1/bets/grupos/{torneo_id}` | ✅ | Grupos con standings + partidos |
| `GET /api/v1/bets/partidos/{torneo_id}` | ✅ | Partidos pendientes de grupo |
| `GET /api/v1/bets/mis-apuestas/{torneo_id}` | ✅ | Apuestas del usuario autenticado |
| `POST /api/v1/bets/apuestas` | ✅ | Crear/actualizar apuesta |
| `GET /api/v1/ranking/{torneo_id}` | ✅ | Ranking de apostadores |

### Respuesta esperada por `/api/v1/bets/grupos/{torneo_id}`
```json
[{
  "fase_id": 1,
  "fase_nombre": "Grupo A",
  "partidos_faltantes": 0,
  "partidos_esperados": 6,
  "standings": [{"equipo_id":1,"nombre":"México","logo_url":"...","clasifica":false,"pj":0,...}],
  "partidos": [{"id":1,"local_id":1,"visit_id":2,"local_nombre":"México","visit_nombre":"...","estado":"programado",...}]
}]
```

---

## Archivos clave

| Archivo | Descripción |
|---------|-------------|
| `app/main.py` | Entry point, lifespan, middlewares, rutas estáticas |
| `app/api/v1/router.py` | Router v1 — incluye torneo y apostador_bets |
| `app/api/v1/endpoints/torneo.py` | CRUD torneos + fixture endpoint |
| `app/api/v1/endpoints/apostador_bets.py` | Endpoints de apuestas y ranking |
| `app/api/v1/endpoints/auth.py` | Login, /me, refresh — /me usa dict explícito |
| `app/services/torneo_service.py` | Carga fixture desde API-Football |
| `app/db/session.py` | Sesiones async — `get_db()` para app_db, `get_becbuc_db()` para becbuc |
| `app/db/init_db.py` | Seed roles + superusuario al startup |
| `app/core/config.py` | Settings desde `.env` — incluye DATABASE_BECBUC_URL |
| `app/api/deps.py` | `CurrentUser`, `DBSession`, `BECBUCSession` |
| `app/models/user.py` | User con roles/permissions/sistemas lazy="raise" + Mapped tipado |
| `app/models/role.py` | Role sin relación users (eliminada) |
| `app/crud/user.py` | CRUDUser — _get_with_relations usa selectinload explícito |
| `static/BECBUC-portal.html` | Portal principal (~1450 líneas) |
| `documentacion/migracion_becbuc_db.sql` | Schema completo de becbuc |

---

## Router registrado (`app/api/v1/router.py`)

```python
api_router.include_router(torneo.router, prefix="/torneo", tags=["torneo"])
api_router.include_router(apostador_bets.router, prefix="/bets", tags=["apuestas"])
```

---

## Schemas Pydantic — reglas

```python
# ✅ CORRECTO en Pydantic v2
nombre: str | None = None
telefono: str | None = None

# ❌ INCORRECTO — falla cuando el valor es None en Pydantic v2
nombre: str = None
```

---

## Relación con `C:\Proyectos\BECBUC`

Hay DOS proyectos separados que comparten la BD `becbuc`:
- `C:\proyecto FAST API` — FastAPI backend principal, schema con nombres en **singular**
  - Tablas: `competicion`, `torneo`, `equipo`, `fase`, `partido`, `participacion`, `apuesta`
- `C:\Proyectos\BECBUC` — Backend alternativo con schema en **plural** (legado)
  - Tablas: `competencias`, `fases`, `grupos`, `equipos`, `partidos`
  - El fixture del Mundial 2026 se carga acá con `backend/scripts/fixture_sync.py`

> El portal `http://localhost:8000/BECBUC-portal` usa el backend de `C:\proyecto FAST API` y las tablas en SINGULAR.

---

## UI / Look & Feel (estilo Bet365)

- Fondo oscuro: `#1a1d23`
- Superficie cards: `#242930`
- Borde sutil: `#2e3540`
- Acento principal: `#00a651` (verde)
- Acento secundario: `#E05020` (naranja BECBUC)
- Tipografía: `'Segoe UI', system-ui, sans-serif`, base 13px
- Banderas: `flagcdn.com/w20/{codigo}.png`

---

## Estado actual (10-jun-2026)

### ✅ Funcionando
- Backend arranca en puerto 8000
- Todos los endpoints del portal implementados y registrados
- `DATABASE_BECBUC_URL` configurado en `.env`
- Modelos ORM corregidos para SQLAlchemy 2.x async
- Schema Pydantic con tipos opcionales correctos

### ✅ Fix aplicado — login / GET /api/v1/auth/me
- **Problema raíz**: `Mapped[list]` sin tipo en `User.roles` hacía que SQLAlchemy 2.x resolviera la colección como scalar `Role` en vez de `list[Role]`
- **Fix**: `Mapped[list["Role"]]` con tipo explícito + `lazy="raise"` + sin `back_populates`
- **Endpoint /me**: construye dict explícito en vez de pasar ORM a Pydantic
- **Estado**: ✅ funcionando

### ⚠️ Pendiente
- Verificar login funciona tras los fixes de ORM
- Portal Apuestas mostrará lista vacía hasta que haya un torneo con `datos_cargados=true`
- Monitor: integración en main.py + router.py + config.py + requirements.txt
- Tests unitarios monitor

---

## Bugs conocidos y resueltos

| Bug | Causa | Fix |
|-----|-------|-----|
| BOM U+FEFF en archivos Python | Editor guardó con UTF-8 BOM | Leer binario y strip `\xef\xbb\xbf` |
| `lazy="noload"` crash startup | Removido en SQLAlchemy 2.x | Usar `lazy="raise"` |
| Doble carga ORM corrompe colección | `lazy="selectin"` en modelo + `selectinload()` en CRUD | Usar solo `selectinload()` explícito, modelo con `lazy="raise"` |
| `user.roles` retorna scalar | `Mapped[list]` sin tipo en SQLAlchemy 2.x | `Mapped[list["Role"]]` con tipo explícito |
| `nombre: str = None` falla en Pydantic v2 | Sin `Optional` | `nombre: str \| None = None` |
| `_reset_puntajes_todos` rollback bug | `await db.rollback()` en except cancelaba UPDATE | Eliminar rollbacks en except blocks |
