"""
diag_bd_estado.py - Diagnostico rapido del estado de partidos en BD
"""
import asyncio
import asyncpg
import sys

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2

async def main():
    conn = await asyncpg.connect(DB_DSN)

    print("=" * 60)
    print("DIAGNOSTICO BD BECBUC - Torneo", TORNEO_ID)
    print("=" * 60)

    # Fases del torneo
    fases = await conn.fetch("""
        SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
        FROM fase WHERE torneo_id = $1 ORDER BY id
    """, TORNEO_ID)
    print(f"\nFASES ({len(fases)}):")
    for f in fases:
        print(f"  id={f['id']} tipo={f['tipo']:<20} nombre={f['nombre']}")

    # Partidos por rango de numero_fifa
    rows = await conn.fetch("""
        SELECT p.numero_fifa, p.estado,
               COALESCE(el.nombre_es, el.nombre, 'TBD') AS local,
               COALESCE(ev.nombre_es, ev.nombre, 'TBD') AS visitante,
               p.goles_local, p.goles_visitante, f.tipo AS fase_tipo
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    print(f"\nTOTAL PARTIDOS: {len(rows)}")

    # Contar por estado
    estados = {}
    for r in rows:
        estados[r['estado']] = estados.get(r['estado'], 0) + 1
    for est, cnt in estados.items():
        print(f"  {est}: {cnt}")

    # Rango de numero_fifa
    nums = [r['numero_fifa'] for r in rows if r['numero_fifa']]
    if nums:
        print(f"  numero_fifa: {min(nums)} a {max(nums)}")

    # Verificar R32 (73-88)
    r32 = [r for r in rows if r['numero_fifa'] and 73 <= r['numero_fifa'] <= 88]
    print(f"\nPARTIDOS R32 (numero_fifa 73-88): {len(r32)}")
    for p in r32:
        gl = p['goles_local'] if p['goles_local'] is not None else '-'
        gv = p['goles_visitante'] if p['goles_visitante'] is not None else '-'
        print(f"  P{p['numero_fifa']:<3} [{p['estado']:<12}] {p['local']:<24} {gl}-{gv} {p['visitante']}")

    # Si no hay R32, mostrar los partidos de mayor numero_fifa
    if not r32:
        print("\nPARTIDOS CON numero_fifa MAS ALTO (ultimos 20):")
        ultimos = sorted(rows, key=lambda r: r['numero_fifa'] or 0, reverse=True)[:20]
        for p in ultimos:
            print(f"  P{p['numero_fifa']:<3} [{p['fase_tipo']:<20}] {p['estado']:<12} {p['local']} vs {p['visitante']}")

    # Grupos finalizados
    grupos = [r for r in rows if r['fase_tipo'] and 'grupo' in r['fase_tipo'].lower()]
    fin_grupos = [r for r in grupos if r['estado'] == 'finalizado']
    print(f"\nGRUPOS: {len(fin_grupos)}/{len(grupos)} finalizados")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
