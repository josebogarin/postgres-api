"""
fix_estado_partido.py - Resetea estado 'aplazado' a 'programado' para un partido por numero_fifa.
Uso: python fix_estado_partido.py 79
"""
import sys
import asyncio

async def main():
    import asyncpg
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 79

    conn = await asyncpg.connect(
        host="localhost", port=5432,
        user="app_user", database="becbuc"
    )

    row = await conn.fetchrow(
        "SELECT id, estado FROM partido WHERE numero_fifa = $1", num
    )
    if not row:
        print(f"Partido P{num} no encontrado")
        return

    print(f"P{num} actual estado: {row['estado']}")

    if row['estado'] == 'aplazado':
        await conn.execute(
            "UPDATE partido SET estado = 'programado' WHERE numero_fifa = $1", num
        )
        print(f"P{num} estado actualizado: aplazado → programado ✓")
    else:
        print(f"P{num} no requiere cambio (estado={row['estado']})")

    await conn.close()

asyncio.run(main())
