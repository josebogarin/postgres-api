"""
Endpoints de administración — CRUD genérico sobre cualquier tabla.

DDL (estructura):
  GET    /admin/tables                          → listar tablas
  GET    /admin/tables/{table}                  → schema de la tabla
  POST   /admin/tables/{table}/columns          → agregar columna
  DELETE /admin/tables/{table}/columns/{col}    → eliminar columna

DML (registros):
  GET    /admin/tables/{table}/rows             → listar/buscar filas
  POST   /admin/tables/{table}/rows             → crear fila
  GET    /admin/tables/{table}/rows/{pk}        → obtener fila
  PATCH  /admin/tables/{table}/rows/{pk}        → editar fila
  DELETE /admin/tables/{table}/rows/{pk}        → eliminar fila

Acceso exclusivo para superusuarios.
"""

import time
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.deps import CurrentAdmin, CurrentSuperuser, DBSession
from app.core.config import settings
from app.db.session import engine
from app.services import table_crud

# Cache de engines por slug (para no recrear en cada request)
_db_engines: dict[str, Any] = {}

router = APIRouter()


# ── SQL directo ───────────────────────────────────────────────────────────────

class SQLRequest(BaseModel):
    query: str
    limit: int = 500  # protección: máximo 500 filas


@router.post("/sql", summary="Ejecutar SQL")
async def execute_sql(_: CurrentSuperuser, body: SQLRequest) -> dict:
    """
    Ejecuta cualquier consulta SQL y devuelve columnas + filas.
    Solo para superusuarios. Úsalo con cuidado en producción.
    """
    t0 = time.monotonic()
    async with engine.connect() as conn:
        # Si es SELECT, agrega LIMIT automático si no lo tiene
        q = body.query.strip().rstrip(";")
        if q.upper().lstrip().startswith("SELECT") and "LIMIT" not in q.upper():
            q = f"{q} LIMIT {body.limit}"
        result = await conn.execute(text(q))
        # Para DDL/DML sin resultset
        try:
            columns = list(result.keys())
            rows = [
                {col: (str(val) if val is not None else None)
                 for col, val in zip(columns, row)}
                for row in result.fetchall()
            ]
        except Exception:
            columns, rows = [], []
        await conn.commit()
    ms = round((time.monotonic() - t0) * 1000, 1)
    return {"columns": columns, "rows": rows, "count": len(rows), "time_ms": ms}


# ── DDL — estructura de tabla ─────────────────────────────────────────────────

@router.get("/tables", summary="Listar tablas")
async def list_tables(_: CurrentSuperuser) -> list[dict]:
    """Todas las tablas de la BD con su PK y cantidad de columnas."""
    return await table_crud.list_tables(engine)


@router.get("/tables/{table_name}", summary="Schema de una tabla")
async def get_table_schema(table_name: str, _: CurrentSuperuser) -> dict:
    """Columnas, tipos, PK, FK e índices de la tabla."""
    return await table_crud.get_table_schema(engine, table_name)


@router.post(
    "/tables/{table_name}/columns",
    summary="Agregar columna",
    description=(
        "Agrega una columna nueva a la tabla. "
        "Tipos permitidos: text, varchar(n), integer, bigint, boolean, "
        "numeric, timestamp, uuid, jsonb, etc."
    ),
)
async def add_column(
    table_name: str,
    _: CurrentSuperuser,
    col_name: str = Body(..., description="Nombre de la nueva columna"),
    col_type: str = Body(..., description="Tipo PostgreSQL, ej: 'text', 'integer', 'varchar(100)'"),
    nullable: bool = Body(True, description="¿Puede ser NULL?"),
    default: str | None = Body(None, description="Valor por defecto SQL, ej: 'now()', \"'activo'\""),
) -> dict:
    """Devuelve el schema actualizado de la tabla."""
    return await table_crud.add_column(engine, table_name, col_name, col_type, nullable, default)


@router.delete(
    "/tables/{table_name}/columns/{col_name}",
    summary="Eliminar columna",
    description="Elimina la columna de la tabla. No se puede eliminar una columna que es PK.",
)
async def drop_column(table_name: str, col_name: str, _: CurrentSuperuser) -> dict:
    """Devuelve el schema actualizado de la tabla."""
    return await table_crud.drop_column(engine, table_name, col_name)


# ── DML — registros ───────────────────────────────────────────────────────────

@router.get(
    "/tables/{table_name}/rows",
    summary="Buscar / listar filas",
    description=(
        "Lista filas con paginación y búsqueda.\n\n"
        "- **q**: texto libre, busca en todas las columnas VARCHAR/TEXT (ILIKE)\n"
        "- **sort_by**: nombre de columna para ordenar\n"
        "- **order**: `asc` o `desc`\n"
        "- **skip / limit**: paginación\n"
        "- **db_slug**: nombre_bd del sistema externo; vacío = BD principal"
    ),
)
async def list_rows(
    table_name: str,
    _: CurrentAdmin,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=5000),
    sort_by: str | None = Query(None, description="Columna para ordenar"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    q: str | None = Query(None, description="Búsqueda de texto libre"),
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    return await table_crud.list_rows(
        eng, table_name,
        skip=skip, limit=limit,
        sort_by=sort_by, order=order,
        q=q,
    )


@router.post(
    "/tables/{table_name}/rows",
    status_code=201,
    summary="Crear fila",
    description="Inserta un nuevo registro. El body es un JSON con los valores de las columnas.",
)
async def create_row(
    table_name: str,
    data: dict[str, Any],
    _: CurrentAdmin,
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    return await table_crud.create_row(eng, table_name, data)


@router.get("/tables/{table_name}/rows/{pk}", summary="Obtener fila por PK")
async def get_row(
    table_name: str,
    pk: str,
    _: CurrentAdmin,
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    return await table_crud.get_row(eng, table_name, pk)


@router.patch(
    "/tables/{table_name}/rows/{pk}",
    summary="Editar fila",
    description="Actualiza los campos enviados. Los campos no incluidos no se tocan.",
)
async def update_row(
    table_name: str,
    pk: str,
    data: dict[str, Any],
    _: CurrentAdmin,
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    return await table_crud.update_row(eng, table_name, pk, data)


@router.delete(
    "/tables/{table_name}/rows/{pk}",
    status_code=204,
    summary="Eliminar fila",
)
async def delete_row(
    table_name: str,
    pk: str,
    _: CurrentAdmin,
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> None:
    eng = await _get_engine_for_slug(db_slug)
    await table_crud.delete_row(eng, table_name, pk)


# ── Seed diccionario ──────────────────────────────────────────────────────────

@router.post(
    "/seed-diccionario",
    summary="Poblar diccionario de campos",
    description=(
        "Lee information_schema de la BD del sistema indicado y llena la tabla "
        "`diccionario` con todas las columnas del schema public. "
        "El campo `campo` se mapea directamente al nombre de columna. "
        "Omite entradas que ya existen para ese sistema. "
        "Solo para superusuarios."
    ),
)
async def seed_diccionario(
    _: CurrentAdmin,
    id_sistema: int | None = Query(None, description="ID del sistema (requerido)"),
    tablas: list[str] = Query(default=[], description="Tablas/vistas a incluir. Si está vacío, procesa todas."),
) -> dict:
    """
    Sincroniza `diccionario` con el esquema real de la BD del sistema:
    - Inserta columnas nuevas (heredando atributos del mismo campo en otras tablas).
    - Elimina entradas de columnas que ya no existen en la BD.
    - Omite entradas que ya existen sin cambios.
    - Si se pasa `tablas`, solo procesa esas tablas/vistas.
    """
    if id_sistema is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="El parámetro id_sistema es requerido")

    # 1. Leer columnas reales desde information_schema de la BD del sistema
    target_engine = await _get_engine_for_id(id_sistema)
    async with target_engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name, column_name, data_type, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name NOT IN ('alembic_version', 'diccionario')
            ORDER BY table_name, ordinal_position
        """))
        columns = result.fetchall()

    # Filtrar por tablas seleccionadas (si se especificaron)
    if tablas:
        tablas_set = set(tablas)
        columns = [r for r in columns if r[0] in tablas_set]

    # Conjunto de (tabla, campo) que realmente existen en la BD
    real_cols: set[tuple[str, str]] = {(r[0], r[1]) for r in columns}

    async with engine.begin() as conn:
        # 2. Leer todo el diccionario actual de este sistema
        existing_result = await conn.execute(
            text("SELECT id, tabla, campo FROM diccionario WHERE id_sistema = :sid"),
            {"sid": id_sistema},
        )
        existing_rows = existing_result.fetchall()
        existing: dict[tuple[str, str], int] = {(r[1], r[2]): r[0] for r in existing_rows}

        # 3. Leer atributos heredables: todos los campos del sistema agrupados por nombre de campo
        #    Usamos el registro más recientemente actualizado como plantilla.
        heritage_result = await conn.execute(text("""
            SELECT DISTINCT ON (campo)
                campo, alias, descripcion, tipo_dato,
                es_visible, es_solo_lectura, es_obligatorio,
                orden_campo, decimales, texto_ayuda, valor_defecto, multivalor
            FROM diccionario
            WHERE id_sistema = :sid
            ORDER BY campo, actualizar_en DESC
        """), {"sid": id_sistema})
        heritage: dict[str, dict] = {
            r[0]: {
                "alias":           r[1],
                "descripcion":     r[2],
                "tipo_dato":       r[3],
                "es_visible":      r[4],
                "es_solo_lectura": r[5],
                "es_obligatorio":  r[6],
                "orden_campo":     r[7],
                "decimales":       r[8],
                "texto_ayuda":     r[9],
                "valor_defecto":   r[10],
                "multivalor":      r[11],
            }
            for r in heritage_result.fetchall()
        }

        # 4. Eliminar entradas obsoletas (campo ya no existe en la BD real)
        deleted = 0
        for (tabla, campo), dic_id in existing.items():
            if (tabla, campo) not in real_cols:
                await conn.execute(
                    text("DELETE FROM diccionario WHERE id = :id"), {"id": dic_id}
                )
                deleted += 1

        # 5. Insertar columnas nuevas (con herencia de atributos si corresponde)
        inserted = 0
        skipped  = 0
        for row in columns:
            tabla_origen, campo, tipo_dato_bd, orden = row[0], row[1], row[2], row[3]
            if (tabla_origen, campo) in existing:
                skipped += 1
                continue

            # Heredar atributos del mismo campo en otras tablas del sistema
            h = heritage.get(campo, {})
            await conn.execute(text("""
                INSERT INTO diccionario
                    (tabla, campo, alias, descripcion, tipo_dato,
                     es_visible, es_solo_lectura, es_obligatorio,
                     orden_campo, decimales, texto_ayuda, valor_defecto, multivalor,
                     id_sistema, crear_en, actualizar_en)
                VALUES (
                    :tabla, :campo, :alias, :descripcion, :tipo_dato,
                    :es_visible, :es_solo_lectura, :es_obligatorio,
                    :orden_campo, :decimales, :texto_ayuda, :valor_defecto, :multivalor,
                    :sid, now(), now()
                )
            """), {
                "tabla":           tabla_origen,
                "campo":           campo,
                "alias":           h.get("alias"),
                "descripcion":     h.get("descripcion"),
                "tipo_dato":       h.get("tipo_dato") or tipo_dato_bd,
                "es_visible":      h.get("es_visible", True),
                "es_solo_lectura": h.get("es_solo_lectura", False),
                "es_obligatorio":  h.get("es_obligatorio", False),
                "orden_campo":     h.get("orden_campo", orden),
                "decimales":       h.get("decimales"),
                "texto_ayuda":     h.get("texto_ayuda"),
                "valor_defecto":   h.get("valor_defecto"),
                "multivalor":      h.get("multivalor"),
                "sid":             id_sistema,
            })
            inserted += 1

    return {
        "inserted":      inserted,
        "skipped":       skipped,
        "deleted":       deleted,
        "total_columns": len(columns),
        "id_sistema":    id_sistema,
        "message": (
            f"Sincronización completa: {inserted} agregados, "
            f"{skipped} sin cambios, {deleted} eliminados."
        ),
    }


# ── Helpers multi-DB ─────────────────────────────────────────────────────────

async def _get_engine_for_slug(slug: str | None):
    """Retorna el engine de la BD indicada por nombre_bd (slug), o el principal si slug es None.

    Estrategia de resolución:
    1. Si el registro en `sistema` tiene host/user/password completos → usa esas credenciales.
    2. Si no → deriva la URL del DATABASE_URL principal reemplazando solo el nombre de BD.
       Esto funciona en el entorno Docker donde todas las BDs viven en el mismo servidor.
    """
    if not slug:
        return engine
    if slug in _db_engines:
        return _db_engines[slug]

    # Buscar credenciales en tabla sistema por nombre_bd
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT host_bd, puerto_bd, nombre_bd, usuario_bd, "contraseña_bd"
                FROM sistema
                WHERE nombre_bd = :slug AND es_activo = true
            """),
            {"slug": slug},
        )
        row = result.fetchone()

    if row:
        host, port, dbname, user, password = row
        if host and user and password:
            db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port or 5432}/{dbname}"
            eng = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2)
            _db_engines[slug] = eng
            return eng

    # Fallback: mismas credenciales/host que DATABASE_URL principal, solo cambia la BD
    # Ej: postgresql+asyncpg://app_user:pass@localhost:5432/app_db → .../becbuc
    main_url = str(settings.DATABASE_URL)
    base_url = main_url.rsplit("/", 1)[0]
    derived_url = f"{base_url}/{slug}"
    eng = create_async_engine(derived_url, echo=False, pool_pre_ping=True, pool_size=2)
    _db_engines[slug] = eng
    return eng


async def _get_engine_for_id(id_sistema: int):
    """Retorna el engine de la BD del sistema indicado por su ID numérico."""
    cache_key = f"__id_{id_sistema}"
    if cache_key in _db_engines:
        return _db_engines[cache_key]
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT host_bd, puerto_bd, nombre_bd, usuario_bd, "contraseña_bd"
                FROM sistema
                WHERE id = :id AND es_activo = true
            """),
            {"id": id_sistema},
        )
        row = result.fetchone()
    if not row:
        return engine
    host, port, dbname, user, password = row
    db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    eng = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2)
    _db_engines[cache_key] = eng
    return eng


# ── Tablas de una BD específica ───────────────────────────────────────────────

@router.get("/db-tables", summary="Listar tablas de una BD por slug")
async def list_tables_by_db(
    current_user: CurrentAdmin,
    db_slug:    str | None = Query(None, description="Slug de la BD. Vacío = BD principal."),
    id_sistema: int | None = Query(None, description="ID del sistema para leer catalogo_objeto."),
) -> dict:
    """
    Devuelve tablas y vistas del schema public de la BD indicada.
    Si se pasa id_sistema, enriquece con alias y filtra objetos solo_superadmin
    según el rol del usuario.
    """
    eng = await _get_engine_for_slug(db_slug)
    async with eng.connect() as conn:
        t_res = await conn.execute(text("""
            SELECT table_name AS name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
              AND table_name != 'alembic_version'
            ORDER BY table_name
        """))
        v_res = await conn.execute(text("""
            SELECT table_name AS name
            FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        raw_tables = [r[0] for r in t_res.fetchall()]
        raw_views  = [r[0] for r in v_res.fetchall()]

    # Leer catálogo si hay id_sistema
    catalogo: dict[str, dict] = {}
    if id_sistema:
        async with engine.connect() as conn:
            rows = await conn.execute(text("""
                SELECT nombre, tipo, alias, solo_superadmin, sql_definicion
                FROM catalogo_objeto
                WHERE id_sistema = :sid AND es_activo = true
            """), {"sid": id_sistema})
            for r in rows.fetchall():
                catalogo[r[0]] = {
                    "alias":           r[2],
                    "solo_superadmin": r[3],
                    "sql_definicion":  r[4],
                }

    is_super = current_user.is_superuser

    def build_item(name: str) -> dict | None:
        cfg = catalogo.get(name, {})
        if cfg.get("solo_superadmin") and not is_super:
            return None
        return {
            "name":            name,
            "alias":           cfg.get("alias") or name,
            "solo_superadmin": cfg.get("solo_superadmin", False),
            "sql_definicion":  cfg.get("sql_definicion") if is_super else None,
        }

    tables = [item for t in raw_tables if (item := build_item(t)) is not None]
    views  = [item for v in raw_views  if (item := build_item(v)) is not None]
    return {"tables": tables, "views": views}


# ── Seed catálogo de objetos ──────────────────────────────────────────────────

@router.post("/seed-catalogo", summary="Auto-poblar catalogo_objeto desde information_schema")
async def seed_catalogo(
    _: CurrentAdmin,
    id_sistema: int = Query(..., description="ID del sistema a catalogar"),
) -> dict:
    """
    Lee todas las tablas y vistas de la BD del sistema e inserta filas en
    catalogo_objeto (ON CONFLICT DO NOTHING — preserva alias y configuraciones).
    Para vistas captura la definición SQL via pg_get_viewdef().
    """
    target_engine = await _get_engine_for_id(id_sistema)
    async with target_engine.connect() as conn:
        t_res = await conn.execute(text("""
            SELECT table_name, 'tabla' AS tipo, NULL AS sql_def
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
              AND table_name != 'alembic_version'
        """))
        v_res = await conn.execute(text("""
            SELECT v.table_name, 'vista' AS tipo,
                   pg_get_viewdef(v.table_name::regclass, true) AS sql_def
            FROM information_schema.views v
            WHERE v.table_schema = 'public'
        """))
        objects = [(r[0], r[1], r[2]) for r in t_res.fetchall() + v_res.fetchall()]

    inserted = 0
    updated  = 0
    async with engine.begin() as conn:
        for nombre, tipo, sql_def in objects:
            # Insertar si no existe
            res_ins = await conn.execute(text("""
                INSERT INTO catalogo_objeto (id_sistema, nombre, tipo, sql_definicion)
                VALUES (:sid, :nombre, :tipo, :sql_def)
                ON CONFLICT (id_sistema, nombre) DO NOTHING
            """), {"sid": id_sistema, "nombre": nombre, "tipo": tipo, "sql_def": sql_def})
            if res_ins.rowcount:
                inserted += 1
            elif tipo == 'vista' and sql_def:
                # Actualizar sql_definicion si cambió (vistas pueden redefinirse)
                res_upd = await conn.execute(text("""
                    UPDATE catalogo_objeto
                    SET sql_definicion = :sql_def, updated_at = NOW()
                    WHERE id_sistema = :sid AND nombre = :nombre
                      AND (sql_definicion IS DISTINCT FROM :sql_def)
                """), {"sid": id_sistema, "nombre": nombre, "sql_def": sql_def})
                if res_upd.rowcount:
                    updated += 1

    return {
        "total":    len(objects),
        "inserted": inserted,
        "updated":  updated,
        "skipped":  len(objects) - inserted - updated,
    }


# ── Schema de tabla en BD específica ─────────────────────────────────────────

@router.get("/db-table-schema", summary="Schema de tabla en BD por slug")
async def get_table_schema_by_db(
    table_name: str,
    _: CurrentAdmin,
    db_slug: str | None = Query(None),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    async with eng.connect() as conn:
        col_res = await conn.execute(text(f"""
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_pk,
                CASE WHEN fk.column_name IS NOT NULL THEN true ELSE false END AS is_fk,
                CASE WHEN uq.column_name  IS NOT NULL THEN true ELSE false END AS is_uq,
                CASE WHEN ix.column_name  IS NOT NULL THEN true ELSE false END AS is_idx
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type='PRIMARY KEY' AND tc.table_schema='public' AND ku.table_name='{table_name}'
            ) pk ON pk.column_name = c.column_name
            LEFT JOIN (
                SELECT ku.column_name FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema='public' AND ku.table_name='{table_name}'
            ) fk ON fk.column_name = c.column_name
            LEFT JOIN (
                SELECT ku.column_name FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type='UNIQUE' AND tc.table_schema='public' AND ku.table_name='{table_name}'
            ) uq ON uq.column_name = c.column_name
            LEFT JOIN (
                SELECT a.attname AS column_name FROM pg_index i
                JOIN pg_class t ON t.oid=i.indrelid
                JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=ANY(i.indkey)
                WHERE NOT i.indisprimary AND t.relname='{table_name}'
            ) ix ON ix.column_name = c.column_name
            WHERE c.table_schema='public' AND c.table_name='{table_name}'
            ORDER BY c.ordinal_position
        """))
        columns = [{
            "name":           r[0],
            "type":           r[1],
            "nullable":       r[2] == "YES",
            "is_primary_key": r[3],
            "is_foreign_key": r[4],
            "is_unique":      r[5],
            "is_index":       r[6],
        } for r in col_res.fetchall()]
    return {"table": table_name, "columns": columns}


# ── SQL de vista + guardar ────────────────────────────────────────────────────

@router.get("/view-sql", summary="SQL de definición de una vista")
async def get_view_sql(
    view_name: str,
    _: CurrentAdmin,
    db_slug: str | None = Query(None),
) -> dict:
    eng = await _get_engine_for_slug(db_slug)
    async with eng.connect() as conn:
        r = await conn.execute(text("""
            SELECT view_definition
            FROM information_schema.views
            WHERE table_schema = 'public'
              AND table_name   = :vn
        """), {"vn": view_name})
        row = r.fetchone()
        if not row or not row[0]:
            raise HTTPException(404, detail=f"Vista '{view_name}' no encontrada")
    return {"view": view_name, "sql": row[0]}


class SaveViewBody(BaseModel):
    view_name: str
    sql: str
    db_slug: str | None = None


@router.post("/save-view", summary="Guardar (recrear) una vista con nuevo SQL")
async def save_view(_: CurrentAdmin, body: SaveViewBody) -> dict:
    from sqlalchemy.exc import SQLAlchemyError
    sql_clean = body.sql.strip().rstrip(";")
    eng = await _get_engine_for_slug(body.db_slug)
    try:
        async with eng.begin() as conn:
            await conn.execute(text(
                f"CREATE OR REPLACE VIEW {body.view_name} AS {sql_clean}"
            ))
    except SQLAlchemyError as e:
        raise HTTPException(400, detail=str(e.orig or e))
    return {"ok": True, "view": body.view_name}


# ── Smart Fill: inferencia de diccionario desde esquema BD ───────────────────

class SmartFillResult(BaseModel):
    campo: str
    alias: str | None
    tipo_dato: str | None
    texto_ayuda: str | None
    multivalor: str | None
    es_solo_lectura: bool
    es_visible: bool
    orden_campo: int | None
    is_new: bool
    changed: bool


@router.post("/smart-fill-dic", summary="Inferir y opcionalmente guardar diccionario desde esquema BD")
async def smart_fill_dic(
    _: CurrentAdmin,
    db: DBSession,
    table_name: str = Query(..., description="Nombre de tabla/vista a analizar"),
    id_sistema: int = Query(..., description="ID del sistema en app_db"),
    save: bool = Query(False, description="Si true, aplica los cambios al diccionario"),
    db_slug: str | None = Query(None, description="Slug de la BD externa; vacío = principal"),
) -> dict:
    """
    Infiere alias, tipo_dato, texto_ayuda, es_solo_lectura, orden_campo para cada
    campo de la tabla a partir de:
    - Nombre del campo (convenciones: id, created_at, id_X, X_id, is_/es_…)
    - Tipo de dato PostgreSQL
    - FK constraints (id_X → referencia a tabla X)
    - Comentarios de columna en pg_description
    Si save=true, hace upsert en la tabla diccionario (app_db).
    Retorna lista de propuestas con indicador is_new/changed.
    """

    # ── 1. Leer columnas + tipo + PK + ordinal desde BD target ────────────────
    target_eng = await _get_engine_for_slug(db_slug)
    async with target_eng.connect() as conn:
        col_res = await conn.execute(text("""
            SELECT
                c.column_name,
                c.data_type,
                c.ordinal_position,
                c.is_nullable,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END AS is_pk
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT ku.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                  ON tc.constraint_name = ku.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                  AND ku.table_name = :tn
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_schema = 'public' AND c.table_name = :tn
            ORDER BY c.ordinal_position
        """), {"tn": table_name})
        columns = col_res.fetchall()

        # ── 2. Leer FK constraints: campo → tabla referenciada ─────────────────
        fk_res = await conn.execute(text("""
            SELECT kcu.column_name, ccu.table_name AS foreign_table
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND kcu.table_schema = 'public'
             AND kcu.table_name = :tn
            JOIN information_schema.referential_constraints rc
              ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON rc.unique_constraint_name = ccu.constraint_name
             AND ccu.table_schema = 'public'
            WHERE tc.constraint_type = 'FOREIGN KEY'
        """), {"tn": table_name})
        fk_map: dict[str, str] = {r[0]: r[1] for r in fk_res.fetchall()}  # campo → tabla referenciada

        # ── 2b. Para cada FK: detectar columna de texto legible ───────────────
        _NAME_COLS = ("nombre", "name", "descripcion", "titulo", "title",
                      "label", "detalle", "codigo", "code", "nombre_es")
        fk_label_col: dict[str, str] = {}
        for campo_fk, ref_table in fk_map.items():
            cols_res = await conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :tn
                ORDER BY ordinal_position
            """), {"tn": ref_table})
            ref_cols = [r[0] for r in cols_res.fetchall()]
            label = next((c for c in _NAME_COLS if c in ref_cols), ref_cols[1] if len(ref_cols) > 1 else "id")
            fk_label_col[campo_fk] = label

        # ── 3. Leer comentarios de columna (pg_description) ──────────────────
        comment_res = await conn.execute(text("""
            SELECT a.attname, pg_catalog.col_description(c.oid, a.attnum)
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
            WHERE c.relname = :tn AND c.relnamespace = (
                SELECT oid FROM pg_catalog.pg_namespace WHERE nspname = 'public'
            )
        """), {"tn": table_name})
        comments: dict[str, str] = {r[0]: r[1] for r in comment_res.fetchall() if r[1]}

    # ── 4. Leer diccionario actual para este sistema + tabla ──────────────────
    existing_result = await db.execute(text("""
        SELECT campo, alias, tipo_dato, texto_ayuda, es_solo_lectura, es_visible, orden_campo, id
        FROM diccionario
        WHERE id_sistema = :sid AND tabla = :tn
    """), {"sid": id_sistema, "tn": table_name})
    existing: dict[str, dict] = {}
    for r in existing_result.fetchall():
        existing[r[0]] = {
            "alias": r[1], "tipo_dato": r[2], "texto_ayuda": r[3],
            "es_solo_lectura": r[4], "es_visible": r[5], "orden_campo": r[6], "id": r[7],
        }

    # ── 5. Mapeo tipo PG → tipo_dato semántico ────────────────────────────────
    def _pg_to_tipo(pg_type: str) -> str:
        pg_type = (pg_type or "").lower()
        if pg_type in ("bigint", "integer", "smallint", "int4", "int8", "int2"):
            return "numero"
        if pg_type in ("boolean",):
            return "booleano"
        if "timestamp" in pg_type or pg_type in ("date",):
            return "fecha"
        if pg_type in ("time without time zone", "time with time zone"):
            return "hora"
        if pg_type in ("numeric", "real", "double precision", "float4", "float8", "decimal"):
            return "decimal"
        if pg_type in ("jsonb", "json"):
            return "json"
        if pg_type in ("uuid",):
            return "texto"
        if pg_type in ("bytea",):
            return "binario"
        return "texto"

    # ── 6. Inferir alias legible desde nombre de campo ────────────────────────
    _STOP = {"id", "de", "del", "la", "el", "en", "y", "a", "por", "con"}

    def _title(s: str) -> str:
        words = s.replace("_", " ").split()
        return " ".join(
            w.capitalize() if w.lower() not in _STOP or i == 0 else w.lower()
            for i, w in enumerate(words)
        )

    def _infer_alias(campo: str, pg_type: str, is_pk: bool, fk_table: str | None) -> str:
        c = campo.lower()
        # PK simple "id"
        if c == "id":
            return "ID"
        # FK detectada por constraint
        if fk_table:
            return _title(fk_table)
        # Convención id_tabla o tabla_id
        if c.startswith("id_"):
            return _title(c[3:])
        if c.endswith("_id"):
            return _title(c[:-3])
        # Campos de fecha típicos
        if c in ("created_at", "crear_en", "fecha_creacion", "fecha_creado"):
            return "Fecha creación"
        if c in ("updated_at", "actualizar_en", "fecha_modificacion", "fecha_actualizacion"):
            return "Fecha modificación"
        if c in ("deleted_at", "fecha_borrado"):
            return "Fecha eliminación"
        # Booleanos es_/is_
        if c.startswith("es_"):
            return _title(c[3:])
        if c.startswith("is_"):
            return _title(c[3:])
        return _title(campo)

    def _infer_readonly(campo: str, is_pk: bool, pg_type: str) -> bool:
        c = campo.lower()
        if is_pk:
            return True
        if c in ("created_at", "crear_en", "updated_at", "actualizar_en",
                  "deleted_at", "fecha_creacion", "fecha_modificacion"):
            return True
        return False

    def _infer_visible(campo: str, is_pk: bool) -> bool:
        c = campo.lower()
        # Ocultar campos de auditoría y PK numérica
        if c in ("deleted_at", "created_at", "updated_at", "crear_en", "actualizar_en"):
            return False
        if is_pk:
            return False
        return True

    def _infer_multivalor(campo: str, fk_table: str | None, label_col: str | None) -> str | None:
        if not fk_table:
            return None
        lc = label_col or "id"
        return f"SELECT id, {lc} AS nombre FROM {fk_table} ORDER BY {lc}"

    def _infer_ayuda(campo: str, pg_type: str, fk_table: str | None) -> str | None:
        c = campo.lower()
        if fk_table:
            return f"Referencia a {_title(fk_table)}"
        if c.endswith("_email") or c == "email":
            return "Correo electrónico"
        if c.endswith("_url") or c == "url":
            return "Dirección URL"
        if c.endswith("_telefono") or c in ("telefono", "phone"):
            return "Número de teléfono"
        if c in ("password", "contraseña", "hash_password"):
            return "Contraseña (encriptada)"
        return None

    # ── 7. Generar propuestas ─────────────────────────────────────────────────
    proposals: list[SmartFillResult] = []
    for row in columns:
        campo, pg_type, ordinal, nullable, is_pk = row[0], row[1], row[2], row[3], row[4]
        fk_table  = fk_map.get(campo)
        label_col = fk_label_col.get(campo)
        comment   = comments.get(campo)

        alias       = _infer_alias(campo, pg_type, is_pk, fk_table)
        tipo_dato   = _pg_to_tipo(pg_type)
        readonly    = _infer_readonly(campo, is_pk, pg_type)
        visible     = _infer_visible(campo, is_pk)
        texto_ayuda = comment or _infer_ayuda(campo, pg_type, fk_table)
        multivalor  = _infer_multivalor(campo, fk_table, label_col)

        prev = existing.get(campo, {})
        is_new = campo not in existing
        changed = not is_new and bool(
            prev.get("alias") != alias or
            prev.get("tipo_dato") != tipo_dato or
            prev.get("texto_ayuda") != texto_ayuda or
            prev.get("es_solo_lectura") != readonly or
            (multivalor is not None and prev.get("multivalor") != multivalor)
        )

        proposals.append(SmartFillResult(
            campo=campo,
            alias=alias,
            tipo_dato=tipo_dato,
            texto_ayuda=texto_ayuda,
            multivalor=multivalor,
            es_solo_lectura=readonly,
            es_visible=visible,
            orden_campo=ordinal,
            is_new=is_new,
            changed=changed,
        ))

    # ── 8. Si save=true: upsert en diccionario ────────────────────────────────
    if save:
        from app.crud.diccionario import diccionario_crud
        from app.schemas.diccionario import DiccionarioCreate, DiccionarioUpdate

        for p in proposals:
            prev = existing.get(p.campo)
            if prev:
                if p.changed:
                    await diccionario_crud.update(
                        db,
                        db_obj=await diccionario_crud.get(db, id=prev["id"]),
                        obj_in=DiccionarioUpdate(
                            alias=p.alias,
                            tipo_dato=p.tipo_dato,
                            texto_ayuda=p.texto_ayuda,
                            multivalor=p.multivalor,
                            es_solo_lectura=p.es_solo_lectura,
                            es_visible=p.es_visible,
                            orden_campo=p.orden_campo,
                        ),
                    )
            else:
                await diccionario_crud.create(
                    db,
                    obj_in=DiccionarioCreate(
                        tabla=table_name,
                        campo=p.campo,
                        alias=p.alias,
                        tipo_dato=p.tipo_dato,
                        texto_ayuda=p.texto_ayuda,
                        multivalor=p.multivalor,
                        es_solo_lectura=p.es_solo_lectura,
                        es_visible=p.es_visible,
                        orden_campo=p.orden_campo,
                        id_sistema=id_sistema,
                    ),
                )

    new_count     = sum(1 for p in proposals if p.is_new)
    changed_count = sum(1 for p in proposals if p.changed)
    return {
        "table": table_name,
        "proposals": [p.model_dump() for p in proposals],
        "total": len(proposals),
        "new": new_count,
        "changed": changed_count,
        "saved": save,
    }


# ── SQL en BD específica ──────────────────────────────────────────────────────

class SQLRequestExt(BaseModel):
    query: str
    limit: int = 500
    db_slug: str | None = None   # None = BD principal


@router.post("/mv-options", summary="Opciones de combo multivalor (SELECT-only, accesible por admin)")
async def get_mv_options(_: CurrentAdmin, body: SQLRequestExt) -> dict:
    """Ejecuta un SELECT para poblar opciones de combos (multivalor en diccionario).
    Solo acepta sentencias SELECT. Accesible por CurrentAdmin."""
    from sqlalchemy.exc import SQLAlchemyError
    q = body.query.strip().rstrip(";")
    if not q.upper().lstrip().startswith("SELECT"):
        raise HTTPException(status_code=400, detail="Solo se permiten sentencias SELECT")
    eng = await _get_engine_for_slug(body.db_slug)
    try:
        async with eng.connect() as conn:
            if "LIMIT" not in q.upper():
                q = f"{q} LIMIT {body.limit}"
            result = await conn.execute(text(q))
            columns = list(result.keys())
            rows = [{col: (str(val) if val is not None else None)
                     for col, val in zip(columns, row)} for row in result.fetchall()]
    except SQLAlchemyError as exc:
        import re as _re
        raw  = str(exc).splitlines()[0] if str(exc) else "Error"
        clean = _re.sub(r"^\([^)]+\)\s*(?:<class '[^']+'>:\s*)?", "", raw).strip() or raw
        raise HTTPException(status_code=400, detail=f"Error SQL: {clean}")
    return {"columns": columns, "rows": rows, "count": len(rows)}


@router.post("/sql-db", summary="Ejecutar SQL en BD por slug")
async def execute_sql_by_db(_: CurrentSuperuser, body: SQLRequestExt) -> dict:
    from sqlalchemy.exc import SQLAlchemyError
    eng = await _get_engine_for_slug(body.db_slug)
    t0  = time.monotonic()
    try:
        async with eng.connect() as conn:
            q = body.query.strip().rstrip(";")
            if q.upper().lstrip().startswith("SELECT") and "LIMIT" not in q.upper():
                q = f"{q} LIMIT {body.limit}"
            result = await conn.execute(text(q))
            try:
                columns = list(result.keys())
                rows = [{col: (str(val) if val is not None else None)
                         for col, val in zip(columns, row)} for row in result.fetchall()]
            except Exception:
                columns, rows = [], []
            await conn.commit()
    except SQLAlchemyError as exc:
        import re as _re
        raw = str(exc).splitlines()[0] if str(exc) else "Error desconocido"
        # Quitar wrapper SQLAlchemy: "(sqlalchemy...Error) <class '...'>: MESSAGE"
        clean = _re.sub(r"^\([^)]+\)\s*(?:<class '[^']+'>:\s*)?", "", raw).strip()
        if not clean:
            clean = raw
        raise HTTPException(status_code=400, detail=f"Error SQL: {clean}")
    ms = round((time.monotonic() - t0) * 1000, 1)
    return {"columns": columns, "rows": rows, "count": len(rows), "time_ms": ms}


# ── Cabecera-Detalle: configuración y detección de FK ────────────────────────

@router.get("/cabecera-config", summary="Configuración cabecera-detalle")
async def get_cabecera_config(
    _: CurrentSuperuser,
    db: DBSession,
    id_sistema: int = Query(..., description="ID del sistema en app_db"),
    tabla: str | None = Query(None, description="Nombre de la tabla cabecera. Si se omite, devuelve todos los nombres."),
) -> dict:
    """
    Con tabla: devuelve la config cabecera + detalles para esa tabla.
    Sin tabla: devuelve la lista de nombres de cabeceras del sistema (para redireccionamiento).
    """
    if tabla:
        r = await db.execute(
            text("SELECT id, nombre, descripcion FROM cabecera WHERE nombre = :t AND id_sistema = :s AND es_activo = true LIMIT 1"),
            {"t": tabla, "s": id_sistema},
        )
        cab = r.fetchone()
        if not cab:
            return {"cabecera": None, "detalles": []}
        dr = await db.execute(
            text("SELECT id, nombre, descripcion, campo_fk FROM detalle WHERE id_cabecera = :c AND es_activo = true ORDER BY id"),
            {"c": cab.id},
        )
        detalles = [{"id": d.id, "nombre": d.nombre, "descripcion": d.descripcion, "campo_fk": d.campo_fk}
                    for d in dr.fetchall()]
        return {"cabecera": {"id": cab.id, "nombre": cab.nombre, "descripcion": cab.descripcion}, "detalles": detalles}
    else:
        r = await db.execute(
            text("SELECT nombre FROM cabecera WHERE id_sistema = :s AND es_activo = true ORDER BY nombre"),
            {"s": id_sistema},
        )
        return {"cabeceras": [row.nombre for row in r.fetchall()]}


@router.get("/detect-fk", summary="Detectar FK de detalle hacia cabecera")
async def detect_fk(
    _: CurrentSuperuser,
    cabecera_table: str = Query(...),
    detalle_table: str = Query(...),
    db_slug: str | None = Query(None),
) -> dict:
    """
    Detecta la columna FK en detalle_table que referencia a cabecera_table.
    Busca primero por FK constraint formal, luego por convención de nombre (id_{cabecera}).
    """
    eng = await _get_engine_for_slug(db_slug)
    async with eng.connect() as conn:
        # 1. FK constraint formal
        r = await conn.execute(text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND kcu.table_schema = 'public'
            JOIN information_schema.referential_constraints rc
              ON tc.constraint_name = rc.constraint_name
            JOIN information_schema.key_column_usage ccu
              ON rc.unique_constraint_name = ccu.constraint_name AND ccu.table_schema = 'public'
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND kcu.table_name = :det
              AND ccu.table_name = :cab
            LIMIT 1
        """), {"det": detalle_table, "cab": cabecera_table})
        row = r.fetchone()
        if row:
            return {"campo_fk": row[0], "source": "constraint"}

        # 2. Convención: id_{cabecera} o {cabecera}_id
        candidates = [f"id_{cabecera_table}", f"{cabecera_table}_id"]
        r2 = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :det
              AND column_name = ANY(:cands)
            LIMIT 1
        """), {"det": detalle_table, "cands": candidates})
        row2 = r2.fetchone()
        if row2:
            return {"campo_fk": row2[0], "source": "convention"}

    return {"campo_fk": None, "source": "not_found"}


# ── Cabecera CRUD ────────────────────────────────────────────────────────────

class CabeceraIn(BaseModel):
    id_sistema: int
    nombre: str
    descripcion: str | None = None
    icono: str | None = None

class CabeceraUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    icono: str | None = None

@router.get("/cabeceras", summary="Listar cabeceras de un sistema")
async def list_cabeceras(
    _: CurrentSuperuser,
    db: DBSession,
    id_sistema: int = Query(...),
) -> list[dict]:
    r = await db.execute(
        text("""
            SELECT id, id_sistema, nombre, descripcion,
                   '' AS icono, es_activo, created_at, updated_at
            FROM cabecera WHERE id_sistema = :s ORDER BY nombre
        """),
        {"s": id_sistema},
    )
    return [dict(row._mapping) for row in r.fetchall()]


@router.post("/cabeceras", status_code=201, summary="Crear cabecera")
async def create_cabecera(
    _: CurrentSuperuser,
    db: DBSession,
    body: CabeceraIn,
) -> dict:
    r = await db.execute(
        text("""
            INSERT INTO cabecera (id_sistema, nombre, descripcion, es_activo, created_at, updated_at)
            VALUES (:s, :n, :d, true, now(), now())
            RETURNING id, id_sistema, nombre, descripcion, '' AS icono, es_activo
        """),
        {"s": body.id_sistema, "n": body.nombre, "d": body.descripcion},
    )
    await db.commit()
    return dict(r.fetchone()._mapping)


@router.patch("/cabeceras/{cab_id}", summary="Actualizar cabecera")
async def update_cabecera(
    cab_id: int,
    _: CurrentSuperuser,
    db: DBSession,
    body: CabeceraUpdate,
) -> dict:
    sets, params = [], {"id": cab_id}
    if body.nombre is not None:
        sets.append("nombre = :nombre"); params["nombre"] = body.nombre
    if body.descripcion is not None:
        sets.append("descripcion = :descripcion"); params["descripcion"] = body.descripcion
    if not sets:
        raise HTTPException(status_code=422, detail="No hay campos para actualizar")
    sets.append("updated_at = now()")
    r = await db.execute(
        text(f"UPDATE cabecera SET {', '.join(sets)} WHERE id = :id RETURNING id, nombre, descripcion, '' AS icono, es_activo"),
        params,
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cabecera no encontrada")
    await db.commit()
    return dict(row._mapping)


@router.delete("/cabeceras/{cab_id}", status_code=204, summary="Eliminar cabecera y sus detalles")
async def delete_cabecera(
    cab_id: int,
    _: CurrentSuperuser,
    db: DBSession,
) -> None:
    await db.execute(text("DELETE FROM detalle WHERE id_cabecera = :id"), {"id": cab_id})
    r = await db.execute(text("DELETE FROM cabecera WHERE id = :id RETURNING id"), {"id": cab_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Cabecera no encontrada")
    await db.commit()


# ── Detalle CRUD ─────────────────────────────────────────────────────────────

class DetalleIn(BaseModel):
    id_cabecera: int
    nombre: str
    descripcion: str | None = None
    campo_fk: str | None = None
    icono: str | None = None

class DetalleUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    campo_fk: str | None = None
    icono: str | None = None

@router.get("/detalles", summary="Listar detalles de una cabecera")
async def list_detalles(
    _: CurrentSuperuser,
    db: DBSession,
    id_cabecera: int = Query(...),
) -> list[dict]:
    r = await db.execute(
        text("""
            SELECT id, id_cabecera, nombre, descripcion, campo_fk,
                   '' AS icono, es_activo
            FROM detalle WHERE id_cabecera = :c ORDER BY id
        """),
        {"c": id_cabecera},
    )
    return [dict(row._mapping) for row in r.fetchall()]


@router.post("/detalles", status_code=201, summary="Crear detalle")
async def create_detalle(
    _: CurrentSuperuser,
    db: DBSession,
    body: DetalleIn,
) -> dict:
    r = await db.execute(
        text("""
            INSERT INTO detalle (id_cabecera, nombre, descripcion, campo_fk, es_activo, created_at, updated_at)
            VALUES (:c, :n, :d, :fk, true, now(), now())
            RETURNING id, id_cabecera, nombre, descripcion, campo_fk, '' AS icono, es_activo
        """),
        {"c": body.id_cabecera, "n": body.nombre, "d": body.descripcion, "fk": body.campo_fk},
    )
    await db.commit()
    return dict(r.fetchone()._mapping)


@router.patch("/detalles/{det_id}", summary="Actualizar detalle")
async def update_detalle(
    det_id: int,
    _: CurrentSuperuser,
    db: DBSession,
    body: DetalleUpdate,
) -> dict:
    sets, params = [], {"id": det_id}
    if body.nombre is not None:
        sets.append("nombre = :nombre"); params["nombre"] = body.nombre
    if body.descripcion is not None:
        sets.append("descripcion = :descripcion"); params["descripcion"] = body.descripcion
    if body.campo_fk is not None:
        sets.append("campo_fk = :campo_fk"); params["campo_fk"] = body.campo_fk
    if not sets:
        raise HTTPException(status_code=422, detail="No hay campos para actualizar")
    sets.append("updated_at = now()")
    r = await db.execute(
        text(f"UPDATE detalle SET {', '.join(sets)} WHERE id = :id RETURNING id, nombre, descripcion, campo_fk, '' AS icono, es_activo"),
        params,
    )
    row = r.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    await db.commit()
    return dict(row._mapping)


@router.delete("/detalles/{det_id}", status_code=204, summary="Eliminar detalle")
async def delete_detalle(
    det_id: int,
    _: CurrentSuperuser,
    db: DBSession,
) -> None:
    r = await db.execute(text("DELETE FROM detalle WHERE id = :id RETURNING id"), {"id": det_id})
    if not r.fetchone():
        raise HTTPException(status_code=404, detail="Detalle no encontrado")
    await db.commit()


# ── Sync sistema desde pg_database ───────────────────────────────────────────

@router.post(
    "/sync-sistema",
    summary="Sincronizar sistemas desde PostgreSQL",
    description=(
        "Lee pg_database y registra en la tabla `sistema` cada base de datos "
        "encontrada. Omite las que ya existen por nombre_bd. "
        "Hereda host/puerto/usuario/contraseña del DATABASE_URL configurado."
    ),
)
async def sync_sistema(_: CurrentSuperuser) -> dict:
    """
    Detecta todas las bases de datos en el servidor PostgreSQL
    y las registra automáticamente en la tabla sistema.
    """
    import urllib.parse

    # Parsear DATABASE_URL para extraer host, port, user, password
    url = settings.DATABASE_URL
    url_clean = url.replace("postgresql+asyncpg://", "postgresql://") \
                   .replace("postgresql+psycopg2://", "postgresql://")
    parsed = urllib.parse.urlparse(url_clean)
    db_host     = parsed.hostname or "localhost"
    db_port     = parsed.port or 5432
    db_user     = urllib.parse.unquote(parsed.username or "")
    db_password = urllib.parse.unquote(parsed.password or "")

    async with engine.connect() as conn:
        # 1. Leer todas las BDs del servidor (excluye templates y postgres)
        result = await conn.execute(text("""
            SELECT datname
            FROM pg_database
            WHERE datistemplate = false
              AND datname NOT IN ('postgres')
            ORDER BY datname
        """))
        db_names = [row[0] for row in result.fetchall()]

        # 2. nombre_bd ya registrados en sistema (PK es id bigint, no id_sistema)
        existing_result = await conn.execute(text("SELECT nombre_bd FROM sistema"))
        existing_bds = {row[0] for row in existing_result.fetchall()}

        # 3. Insertar las que faltan
        inserted = 0
        skipped  = 0
        for db_name in db_names:
            if db_name in existing_bds:
                skipped += 1
                continue
            await conn.execute(text("""
                INSERT INTO sistema
                    (nombre, descripcion,
                     host_bd, puerto_bd, nombre_bd, usuario_bd, "contraseña_bd",
                     es_activo, created_at, updated_at)
                VALUES (
                    :nombre, :descripcion,
                    :host_bd, :puerto_bd, :nombre_bd, :usuario_bd, :contrasena_bd,
                    true, now(), now()
                )
            """), {
                "nombre":        db_name,
                "descripcion":   f"Base de datos PostgreSQL: {db_name}",
                "host_bd":       db_host,
                "puerto_bd":     db_port,
                "nombre_bd":     db_name,
                "usuario_bd":    db_user,
                "contrasena_bd": db_password,
            })
            inserted += 1

        await conn.commit()

    return {
        "databases_found": len(db_names),
        "inserted":        inserted,
        "skipped":         skipped,
        "message":         f"Sistemas sincronizados: {inserted} nuevos, {skipped} ya existían.",
    }
