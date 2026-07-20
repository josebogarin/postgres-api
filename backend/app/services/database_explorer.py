"""
Service for exploring PostgreSQL databases, tables, and schemas.
Combines database metadata with dictionary entries for rich information.
"""
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.diccionario import diccionario_crud
from app.db.session import engine


class DatabaseExplorer:
    """Explore PostgreSQL structure and combine with metadata from diccionario."""

    async def get_databases(self, db: AsyncSession) -> list[dict]:
        """List all databases in PostgreSQL server."""
        try:
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        """
                    SELECT datname as name
                    FROM pg_database
                    WHERE datistemplate = false
                    ORDER BY datname
                    """
                    )
                )
                databases = [row[0] for row in result.fetchall()]
                return [{"name": name} for name in databases]
        except Exception as e:
            return {"error": str(e)}

    async def get_tables_and_views(
        self, db: AsyncSession, database_name: str
    ) -> dict:
        """Get all tables and views for a specific database."""
        try:
            async with engine.connect() as conn:
                # Get tables
                tables_result = await conn.execute(
                    text(
                        f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                    )
                )
                tables = [row[0] for row in tables_result.fetchall()]

                # Get views
                views_result = await conn.execute(
                    text(
                        f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'VIEW'
                    ORDER BY table_name
                    """
                    )
                )
                views = [row[0] for row in views_result.fetchall()]

                return {"tables": tables, "views": views}
        except Exception as e:
            return {"error": str(e)}

    async def get_table_schema(
        self, db: AsyncSession, table_name: str
    ) -> dict:
        """Get complete schema for a table with dictionary metadata."""
        try:
            async with engine.connect() as conn:
                # Get columns from information_schema
                result = await conn.execute(
                    text(
                        f"""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                    """
                    )
                )
                columns_info = result.fetchall()

                # Get primary key
                pk_result = await conn.execute(
                    text(
                        f"""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                    AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelname = '{table_name}_pkey'
                    """
                    )
                )
                pk_columns = {row[0] for row in pk_result.fetchall()}

                # Get indexes
                idx_result = await conn.execute(
                    text(
                        f"""
                    SELECT
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename = '{table_name}'
                    """
                    )
                )
                indexes = [row[2] for row in idx_result.fetchall()]

                # Get unique constraints
                unique_result = await conn.execute(
                    text(
                        f"""
                    SELECT column_name
                    FROM information_schema.key_column_usage
                    WHERE table_schema = 'public'
                    AND table_name = '{table_name}'
                    AND constraint_name IN (
                        SELECT constraint_name
                        FROM information_schema.table_constraints
                        WHERE constraint_type = 'UNIQUE'
                    )
                    """
                    )
                )
                unique_columns = {row[0] for row in unique_result.fetchall()}

                # Get foreign keys
                fk_result = await conn.execute(
                    text(
                        f"""
                    SELECT
                        column_name,
                        referenced_table_name,
                        referenced_column_name
                    FROM information_schema.referential_constraints rc
                    JOIN information_schema.key_column_usage kcu
                        ON rc.constraint_name = kcu.constraint_name
                    WHERE kcu.table_schema = 'public'
                    AND kcu.table_name = '{table_name}'
                    """
                    )
                )
                foreign_keys = {
                    row[0]: {"table": row[1], "column": row[2]}
                    for row in fk_result.fetchall()
                }

                # Build columns response
                columns = []
                for col_info in columns_info:
                    col_name = col_info[0]

                    # Get dictionary entry for this column
                    dict_entry = await diccionario_crud.get_by_tabla_columna(
                        db, tabla=table_name, columna=col_name
                    )

                    columns.append(
                        {
                            "name": col_name,
                            "type": col_info[1],
                            "nullable": col_info[2] == "YES",
                            "default": col_info[3],
                            "max_length": col_info[4],
                            "numeric_precision": col_info[5],
                            "numeric_scale": col_info[6],
                            "is_primary_key": col_name in pk_columns,
                            "is_unique": col_name in unique_columns,
                            "foreign_key": foreign_keys.get(col_name),
                            "description": dict_entry.descripcion if dict_entry else None,
                            "is_active": dict_entry.es_activo if dict_entry else True,
                        }
                    )

                return {
                    "table": table_name,
                    "columns": columns,
                    "indexes": indexes,
                    "row_count": await self._get_row_count(conn, table_name),
                }

        except Exception as e:
            return {"error": str(e)}

    async def _get_row_count(self, conn, table_name: str) -> int:
        """Get approximate row count for a table."""
        try:
            result = await conn.execute(
                text(
                    f"""
                SELECT COUNT(*) FROM {table_name}
                """
                )
            )
            return result.scalar()
        except:
            return 0

    async def get_table_data(
        self,
        db: AsyncSession,
        table_name: str,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
    ) -> dict:
        """Get data from a table with optional search."""
        try:
            async with engine.connect() as conn:
                # Get total count
                count_result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                total = count_result.scalar()

                # Build query
                query = f"SELECT * FROM {table_name}"
                if search:
                    # Simple search on all text columns
                    query += f" WHERE CAST(* AS text) ILIKE '%{search}%'"

                query += f" LIMIT {limit} OFFSET {skip}"

                # Get data
                result = await conn.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()

                # Format data
                data = [
                    {str(col): str(val) if val is not None else None
                     for col, val in zip(columns, row)}
                    for row in rows
                ]

                return {
                    "table": table_name,
                    "total": total,
                    "skip": skip,
                    "limit": limit,
                    "columns": list(columns),
                    "data": data,
                }

        except Exception as e:
            return {"error": str(e)}


database_explorer = DatabaseExplorer()
