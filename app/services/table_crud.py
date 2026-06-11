"""
Motor de CRUD genérico basado en reflexión de SQLAlchemy.
Soporta:
  - DDL: agregar y eliminar columnas de cualquier tabla
  - DML: buscar, crear, editar y eliminar registros
Solo para uso administrativo — restringido a superusuarios.
"""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import MetaData, Table, delete, func, insert, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import NotFoundError

# Tablas internas que nunca se exponen
EXCLUDED_TABLES: set[str] = {"alembic_version"}

# Tipos de columna permitidos para DDL (base type en minúsculas)
_ALLOWED_BASE_TYPES: set[str] = {
    "text", "varchar", "character varying", "char", "character",
    "integer", "int", "int4", "bigint", "int8", "smallint", "int2",
    "serial", "bigserial",
    "boolean", "bool",
    "numeric", "decimal", "float", "double precision", "real",
    "timestamp", "timestamptz",
    "timestamp with time zone", "timestamp without time zone",
    "date", "time",
    "uuid",
    "jsonb", "json",
    "bytea",
}

# Identificadores SQL válidos (letras, dígitos, guión bajo; empieza con letra o _)
_VALID_IDENT = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,62}$')


# ── Validación de identificadores ──────────────────────────────────────────────

def _assert_ident(name: str, label: str = "identifier") -> str:
    if not _VALID_IDENT.match(name):
        raise ValueError(f"Invalid {label}: '{name}'")
    return name


def _assert_col_type(col_type: str) -> str:
    """Valida que el tipo de columna sea seguro (whitelist de tipos PostgreSQL)."""
    base = re.split(r'[\s(]', col_type.strip().lower())[0]
    if base not in _ALLOWED_BASE_TYPES:
        raise ValueError(
            f"Type '{col_type}' not allowed. Allowed types: {', '.join(sorted(_ALLOWED_BASE_TYPES))}"
        )
    return col_type.strip()


# ── Serialización ─────────────────────────────────────────────────────────────

def _serialize_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, uuid.UUID):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.hex()
    return val


def _serialize_row(row) -> dict[str, Any]:
    return {k: _serialize_value(v) for k, v in row._mapping.items()}


# ── Reflexión de tabla ────────────────────────────────────────────────────────

async def _reflect_table(engine: AsyncEngine, table_name: str) -> Table:
    _assert_ident(table_name, "table name")
    meta = MetaData()

    def _do_reflect(sync_conn):
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(sync_conn)
        is_table = table_name in insp.get_table_names()
        is_view  = table_name in insp.get_view_names()
        if table_name in EXCLUDED_TABLES or (not is_table and not is_view):
            return False
        meta.reflect(bind=sync_conn, only=[table_name], views=True)
        return True

    async with engine.connect() as conn:
        found = await conn.run_sync(_do_reflect)

    if not found or table_name not in meta.tables:
        raise NotFoundError(f"Table '{table_name}'")

    return meta.tables[table_name]


def _pk_columns(table: Table) -> list[str]:
    return [col.name for col in table.primary_key.columns]


def _parse_pk(table: Table, pk_value: str) -> dict[str, Any]:
    pk_cols = _pk_columns(table)
    if len(pk_cols) != 1:
        raise ValueError("Solo se soportan PKs de una columna por esta interfaz")
    col_name = pk_cols[0]
    col = table.c[col_name]
    type_name = type(col.type).__name__.upper()
    if "UUID" in type_name:
        return {col_name: uuid.UUID(pk_value)}
    if any(t in type_name for t in ("INT", "SERIAL", "BIGINT")):
        return {col_name: int(pk_value)}
    return {col_name: pk_value}


def _validate_columns(table: Table, data: dict[str, Any]) -> dict[str, Any]:
    valid = {col.name for col in table.columns}
    return {k: v for k, v in data.items() if k in valid}


def _coerce_value(col, val: Any) -> Any:
    """Convierte val al tipo Python que asyncpg espera según el tipo de la columna."""
    if val is None:
        return None
    type_name = type(col.type).__name__.upper()
    # Enteros
    if any(t in type_name for t in ("INT", "SERIAL", "BIGINT", "SMALLINT")):
        if isinstance(val, str):
            return int(val) if val.strip() != "" else None
        return int(val) if not isinstance(val, bool) else val
    # Decimales / numerics
    if any(t in type_name for t in ("NUMERIC", "DECIMAL", "FLOAT", "REAL", "DOUBLE")):
        if isinstance(val, str):
            return float(val) if val.strip() != "" else None
        return float(val)
    # Booleano
    if "BOOL" in type_name:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "t", "yes", "si", "sí")
        return bool(val)
    # UUID
    if "UUID" in type_name and isinstance(val, str):
        return uuid.UUID(val)
    # Timestamp / DateTime
    if any(t in type_name for t in ("TIMESTAMP", "DATETIME")) and isinstance(val, str):
        v = val.strip()
        if not v:
            return None
        # Normalizar: reemplazar separador T por espacio, truncar milisegundos
        v = v.replace("T", " ")
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
        return val  # dejar pasar si no matchea ningún formato
    # Date
    if "DATE" in type_name and isinstance(val, str):
        v = val.strip()
        if not v:
            return None
        try:
            return datetime.strptime(v[:10], "%Y-%m-%d").date()
        except ValueError:
            return val
    # Para texto y otros: pasar como está
    return val


def _coerce_data(table: Table, data: dict[str, Any]) -> dict[str, Any]:
    """Aplica _coerce_value a cada campo del dict según el tipo de columna reflejado."""
    result = {}
    for k, v in data.items():
        if k in table.c:
            result[k] = _coerce_value(table.c[k], v)
        else:
            result[k] = v
    return result


def _text_columns(table: Table) -> list[str]:
    """Devuelve columnas de texto (VARCHAR/TEXT) para búsqueda ILIKE."""
    from sqlalchemy import String
    _NAME_FALLBACK = {"VARCHAR", "TEXT", "CHAR", "STRING", "CLOB", "NVARCHAR", "NCHAR"}
    result = []
    for col in table.columns:
        t = col.type
        if isinstance(t, String):          # cubre VARCHAR, TEXT, CHAR y subclases
            result.append(col.name)
        elif type(t).__name__.upper() in _NAME_FALLBACK:   # fallback para dialectos externos
            result.append(col.name)
    return result


def _build_like_pattern(q: str) -> str:
    """
    Prepara el patrón ILIKE para PostgreSQL (case-insensitive).

    El cliente envía el patrón con comodines SQL (%):
      %palabra%  →  contiene   (default cuando no hay comodines)
      palabra%   →  empieza con
      %palabra   →  termina con

    Si q no tiene %, se asume búsqueda "contiene" (%q%).
    """
    q = q.strip()
    if not q:
        return "%"
    return q if "%" in q else f"%{q}%"


# ── Información de tablas ─────────────────────────────────────────────────────

async def list_tables(engine: AsyncEngine) -> list[dict]:
    def _inspect(sync_conn):
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(sync_conn)
        result = []
        for name in sorted(insp.get_table_names()):
            if name in EXCLUDED_TABLES:
                continue
            cols = insp.get_columns(name)
            pk = insp.get_pk_constraint(name).get("constrained_columns", [])
            result.append({
                "name": name,
                "column_count": len(cols),
                "primary_key": pk,
            })
        return result

    async with engine.connect() as conn:
        return await conn.run_sync(_inspect)


async def get_table_schema(engine: AsyncEngine, table_name: str) -> dict:
    _assert_ident(table_name, "table name")

    def _inspect(sync_conn):
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(sync_conn)
        is_table = table_name in insp.get_table_names()
        is_view  = table_name in insp.get_view_names()
        if table_name in EXCLUDED_TABLES or (not is_table and not is_view):
            return None
        cols = insp.get_columns(table_name)
        pk = insp.get_pk_constraint(table_name).get("constrained_columns", []) if is_table else []
        fks = insp.get_foreign_keys(table_name) if is_table else []
        idxs = insp.get_indexes(table_name) if is_table else []
        return {
            "name": table_name,
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": c.get("nullable", True),
                    "default": str(c["default"]) if c.get("default") is not None else None,
                    "primary_key": c["name"] in pk,
                }
                for c in cols
            ],
            "primary_key": pk,
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "references": f"{fk['referred_table']}.{fk['referred_columns']}",
                }
                for fk in fks
            ],
            "indexes": [
                {"name": i["name"], "columns": i["column_names"], "unique": i["unique"]}
                for i in idxs
            ],
        }

    async with engine.connect() as conn:
        schema = await conn.run_sync(_inspect)

    if schema is None:
        raise NotFoundError(f"Table '{table_name}'")
    return schema


# ── DDL helpers ───────────────────────────────────────────────────────────────

async def _clear_idle_in_transaction(conn) -> None:
    """Terminate idle-in-transaction sessions owned by the same user before DDL.

    DDL (ALTER TABLE) needs AccessExclusiveLock. Sessions that committed their
    query but whose asyncpg connection hasn't fully returned to the pool yet
    appear as 'idle in transaction' and block DDL. Terminating them (we can
    because they share the same pg role) releases the locks immediately.
    """
    await conn.execute(text("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE state = 'idle in transaction'
          AND pid != pg_backend_pid()
          AND usename = current_user
    """))


# ── DDL — estructura de tabla ─────────────────────────────────────────────────

async def add_column(
    engine: AsyncEngine,
    table_name: str,
    col_name: str,
    col_type: str,
    nullable: bool = True,
    default: str | None = None,
) -> dict:
    """Agrega una columna a una tabla existente."""
    _assert_ident(table_name, "table name")
    _assert_ident(col_name, "column name")
    _assert_col_type(col_type)

    # Construir la cláusula con identificadores entre comillas dobles (safe)
    null_clause = "" if nullable else " NOT NULL"
    default_clause = f" DEFAULT {default}" if default is not None else ""
    ddl = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type}{default_clause}{null_clause}'

    async with engine.begin() as conn:
        await _clear_idle_in_transaction(conn)
        await conn.execute(text(ddl))

    return await get_table_schema(engine, table_name)


async def drop_column(engine: AsyncEngine, table_name: str, col_name: str) -> dict:
    """Elimina una columna de una tabla. La columna no debe ser parte del PK."""
    _assert_ident(table_name, "table name")
    _assert_ident(col_name, "column name")

    # Verificar que la columna existe y no es PK
    table = await _reflect_table(engine, table_name)
    pk_cols = _pk_columns(table)
    if col_name in pk_cols:
        raise ValueError(f"Column '{col_name}' is part of the primary key and cannot be dropped")
    if col_name not in table.c:
        raise NotFoundError(f"Column '{col_name}' in table '{table_name}'")

    ddl = f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"'
    async with engine.begin() as conn:
        await _clear_idle_in_transaction(conn)
        await conn.execute(text(ddl))

    return await get_table_schema(engine, table_name)


# ── DML — registros ───────────────────────────────────────────────────────────

async def list_rows(
    engine: AsyncEngine,
    table_name: str,
    skip: int = 0,
    limit: int = 50,
    sort_by: str | None = None,
    order: str = "asc",
    q: str | None = None,
    filters: dict[str, str] | None = None,
) -> dict:
    """
    Lista filas con paginación.
    - q: búsqueda de texto libre en todas las columnas VARCHAR/TEXT (ILIKE)
    - filters: dict col→valor para filtros exactos
    """
    table = await _reflect_table(engine, table_name)

    stmt = select(table)
    count_stmt = select(func.count()).select_from(table)

    # Búsqueda libre en columnas de texto (VARCHAR / TEXT) — case-insensitive via ILIKE
    if q:
        like_pat = _build_like_pattern(q)
        text_cols = _text_columns(table)
        if text_cols:
            conditions = [table.c[c].ilike(like_pat) for c in text_cols]
            stmt = stmt.where(or_(*conditions))
            count_stmt = count_stmt.where(or_(*conditions))

    # Filtros exactos por columna
    if filters:
        safe = _validate_columns(table, filters)
        for col_name, val in safe.items():
            stmt = stmt.where(table.c[col_name] == val)
            count_stmt = count_stmt.where(table.c[col_name] == val)

    # Ordenamiento
    if sort_by and sort_by in table.c:
        col = table.c[sort_by]
        stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())

    stmt = stmt.offset(skip).limit(limit)

    async with engine.connect() as conn:
        total = (await conn.execute(count_stmt)).scalar()
        rows = (await conn.execute(stmt)).fetchall()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [_serialize_row(r) for r in rows],
    }


async def get_row(engine: AsyncEngine, table_name: str, pk_value: str) -> dict:
    table = await _reflect_table(engine, table_name)
    pk_filter = _parse_pk(table, pk_value)
    stmt = select(table)
    for col_name, val in pk_filter.items():
        stmt = stmt.where(table.c[col_name] == val)
    async with engine.connect() as conn:
        row = (await conn.execute(stmt)).fetchone()
    if row is None:
        raise NotFoundError(f"Row '{pk_value}' in '{table_name}'")
    return _serialize_row(row)


async def create_row(engine: AsyncEngine, table_name: str, data: dict[str, Any]) -> dict:
    table = await _reflect_table(engine, table_name)
    safe_data = _coerce_data(table, _validate_columns(table, data))

    # Auto-generate UUID for UUID PK columns not provided and with no DB-level default.
    for col in table.primary_key.columns:
        if col.name not in safe_data and col.default is None and col.server_default is None:
            if "UUID" in type(col.type).__name__.upper():
                safe_data[col.name] = uuid.uuid4()

    stmt = insert(table).values(**safe_data).returning(*table.columns)
    async with engine.begin() as conn:
        row = (await conn.execute(stmt)).fetchone()
    return _serialize_row(row)


async def update_row(
    engine: AsyncEngine, table_name: str, pk_value: str, data: dict[str, Any]
) -> dict:
    table = await _reflect_table(engine, table_name)
    pk_filter = _parse_pk(table, pk_value)
    pk_cols = set(_pk_columns(table))
    safe_data = _coerce_data(
        table,
        {k: v for k, v in _validate_columns(table, data).items() if k not in pk_cols}
    )
    if not safe_data:
        return await get_row(engine, table_name, pk_value)
    stmt = update(table).returning(*table.columns)
    for col_name, val in pk_filter.items():
        stmt = stmt.where(table.c[col_name] == val)
    stmt = stmt.values(**safe_data)
    async with engine.begin() as conn:
        row = (await conn.execute(stmt)).fetchone()
    if row is None:
        raise NotFoundError(f"Row '{pk_value}' in '{table_name}'")
    return _serialize_row(row)


async def delete_row(engine: AsyncEngine, table_name: str, pk_value: str) -> None:
    table = await _reflect_table(engine, table_name)
    pk_filter = _parse_pk(table, pk_value)
    stmt = delete(table)
    for col_name, val in pk_filter.items():
        stmt = stmt.where(table.c[col_name] == val)
    async with engine.begin() as conn:
        result = await conn.execute(stmt)
    if result.rowcount == 0:
        raise NotFoundError(f"Row '{pk_value}' in '{table_name}'")
