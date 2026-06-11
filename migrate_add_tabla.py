"""
Migración: agrega columna 'tabla' a la tabla diccionario.
Ejecutar UNA sola vez.

Uso:
    python migrate_add_tabla.py
"""
import asyncio
import asyncpg

DSN = "postgresql://app_user:superpassword@localhost:5432/app_db"

async def main():
    conn = await asyncpg.connect(DSN)

    # Verificar si la columna ya existe
    exists = await conn.fetchval("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name   = 'diccionario'
          AND column_name  = 'tabla'
    """)

    if exists:
        print("La columna 'tabla' ya existe en diccionario. Nada que hacer.")
    else:
        await conn.execute("""
            ALTER TABLE diccionario
            ADD COLUMN tabla VARCHAR(255) DEFAULT NULL
        """)
        # Agregar índice para búsquedas por tabla
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_diccionario_tabla
            ON diccionario (tabla)
        """)
        print("Columna 'tabla' agregada correctamente a diccionario.")

    await conn.close()

asyncio.run(main())
