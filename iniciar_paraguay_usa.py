import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import asyncpg

DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"

async def main():
    conn = await asyncpg.connect(DSN)

    # Buscar partidos de hoy que no están en_juego ni finalizados
    rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.estado, p.fecha,
               el.nombre AS local, ev.nombre AS visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.tipo NOT ILIKE 'grupo%'
          AND DATE(p.fecha AT TIME ZONE 'UTC') = CURRENT_DATE
          AND p.estado IN ('programado', 'pendiente')
        ORDER BY p.fecha
    """)

    if not rows:
        print("No hay mas partidos de hoy pendientes de iniciar.")
        await conn.close()
        return

    print("Partidos de hoy pendientes:")
    for r in rows:
        print(f"  P{r['numero_fifa']} | {r['local']} vs {r['visitante']} | estado={r['estado']} | fecha={r['fecha']}")
        await conn.execute("""
            UPDATE partido SET estado = 'en_juego', minuto_actual = 1
            WHERE id = $1
        """, r['id'])
        print(f"  -> Marcado en_juego OK")

    await conn.close()
    print("\nListo.")

asyncio.run(main())
