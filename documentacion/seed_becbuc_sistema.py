"""
Registra el sistema BECBUC en app_db.
Ejecutar:
    & "C:\proyecto FAST API\backend\.venv\Scripts\python.exe" "C:\proyecto FAST API\documentacion\seed_becbuc_sistema.py"
"""
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        host="localhost", port=5432,
        database="app_db", user="app_user", password="superpassword"
    )

    # Ver si ya existe
    sistema_id = await conn.fetchval("SELECT id FROM sistema WHERE nombre='BECBUC'")

    if not sistema_id:
        # Insertar sin id_sistema primero
        sistema_id = await conn.fetchval("""
            INSERT INTO sistema (nombre, descripcion, host_bd, puerto_bd, nombre_bd, usuario_bd, contraseña_bd, es_activo)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """, "BECBUC", "Sistema de torneos, fixture y apuestas deportivas",
            "localhost", 5432, "becbuc", "app_user", "superpassword", True)

        # id_sistema = id (columna que el ORM usa como alias)
        await conn.execute("UPDATE sistema SET id_sistema = $1 WHERE id = $1", sistema_id)
        print(f"Sistema BECBUC creado (id={sistema_id})")
    else:
        print(f"Sistema BECBUC ya existía (id={sistema_id})")

    # Asignar a todos los superadmin
    count = await conn.execute("""
        INSERT INTO user_sistemas (user_id, sistema_id)
        SELECT u.id, $1
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id AND r.name = 'superadmin'
        ON CONFLICT DO NOTHING
    """, sistema_id)
    print(f"Asignaciones creadas: {count}")

    await conn.close()
    print("Listo.")

asyncio.run(main())
