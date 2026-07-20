import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import asyncpg

DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"

async def main():
    conn = await asyncpg.connect(DSN)

    # Buscar partido de Brasil en KO
    rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.estado, p.fecha,
               el.nombre AS local, ev.nombre AS visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.tipo NOT ILIKE 'grupo%'
          AND (el.nombre ILIKE '%brazil%' OR el.nombre ILIKE '%brasil%'
            OR ev.nombre ILIKE '%brazil%' OR ev.nombre ILIKE '%brasil%')
        ORDER BY p.fecha
    """)

    if not rows:
        print("ERROR: No se encontro partido de Brasil en fases KO.")
        await conn.close()
        return

    print("Partidos de Brasil encontrados:")
    for r in rows:
        print(f"  P{r['numero_fifa']} | id={r['id']} | {r['local']} vs {r['visitante']} | estado={r['estado']} | fecha={r['fecha']}")

    # Tomar el primero no finalizado
    target = None
    for r in rows:
        if r['estado'] != 'finalizado':
            target = r
            break

    if not target:
        print("Todos los partidos de Brasil estan finalizados.")
        await conn.close()
        return

    print(f"\nCambiando estado a 'en_juego': P{target['numero_fifa']} {target['local']} vs {target['visitante']}")
    await conn.execute("""
        UPDATE partido SET estado = 'en_juego', minuto_actual = 1
        WHERE id = $1
    """, target['id'])
    print("Listo! Partido P" + str(target['numero_fifa']) + " ahora esta en_juego.")

    await conn.close()

asyncio.run(main())
