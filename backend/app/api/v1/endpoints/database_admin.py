"""
Database administration endpoints for exploring PostgreSQL structure.
Allows viewing databases, tables, schemas, and data.
"""
from fastapi import APIRouter, Query

from app.api.deps import CurrentSuperuser, DBSession
from app.core.exceptions import NotFoundError
from app.services.database_explorer import database_explorer

router = APIRouter()


@router.get("/databases")
async def list_databases(db: DBSession, _: CurrentSuperuser):
    """
    List all PostgreSQL databases.

    Returns:
        list of database names
    """
    databases = await database_explorer.get_databases(db)
    return databases


@router.get("/databases/{database_name}/tables")
async def list_database_tables(
    database_name: str, db: DBSession, _: CurrentSuperuser
):
    """
    List all tables and views in a specific database.

    Args:
        database_name: Name of the database

    Returns:
        dict with 'tables' and 'views' lists
    """
    result = await database_explorer.get_tables_and_views(db, database_name)
    return result


@router.get("/databases/{database_name}/tables/{table_name}/schema")
async def get_table_schema(
    database_name: str, table_name: str, db: DBSession, _: CurrentSuperuser
):
    """
    Get complete schema for a table.

    Combines PostgreSQL metadata with dictionary entries for descriptions.

    Args:
        database_name: Name of the database
        table_name: Name of the table

    Returns:
        dict with table structure, columns, indexes, and row count
    """
    schema = await database_explorer.get_table_schema(db, table_name)
    if "error" in schema:
        raise NotFoundError(f"Table {table_name}")
    return schema


@router.get("/databases/{database_name}/tables/{table_name}/rows")
async def get_table_data(
    database_name: str,
    table_name: str,
    db: DBSession,
    _: CurrentSuperuser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: str | None = Query(None),
):
    """
    Get all data from a table with pagination and optional search.

    Args:
        database_name: Name of the database
        table_name: Name of the table
        skip: Number of rows to skip
        limit: Number of rows to return
        search: Optional search string

    Returns:
        dict with table data, column names, total count
    """
    data = await database_explorer.get_table_data(
        db, table_name, skip=skip, limit=limit, search=search
    )
    if "error" in data:
        raise NotFoundError(f"Table {table_name}")
    return data
