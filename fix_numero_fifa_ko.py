"""
fix_numero_fifa_ko.py
=====================
Asigna numero_fifa (73-104) a los partidos KO que lo tienen en NULL.
Usa el mismo orden que build_num_maps en ko_scoring.py.
"""
import asyncio
import asyncpg

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2

TIPO_NUMS = {
    "ronda32":       list(range(73, 89)),
    "ronda16":       list(range(89, 97)),
    "cuartos":       list(range(97, 101)),
    "semis":         [101, 102],
    "tercer_puesto": [103],
    "final":         [104],
}

async def main():
    conn = await asyncpg.connect(DB_DSN)
    print("=== Asignar numero_fifa a partidos KO ===\n")

    updated = 0
    for tipo, nums in TIPO_NUMS.items():
        # Obtener partidos de esta fase ordenados por id
        rows = await conn.fetch("""
            SELECT p.id, p.numero_fifa,
                   COALESCE(el.nombre_es, el.nombre, 'TBD') AS local,
                   COALESCE(ev.nombre_es, ev.nombre, 'TBD') AS visitante
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE f.torneo_id = $1 AND f.tipo = $2
            ORDER BY p.id
        """, TORNEO_ID, tipo)

        print(f"[{tipo}] {len(rows)} partidos, esperados {len(nums)}")

        if len(rows) != len(nums):
            print(f"  AVISO: cantidad no coincide ({len(rows)} vs {len(nums)} esperados)")

        for pid_row, num in zip(rows, nums):
            pid = pid_row["id"]
            current_num = pid_row["numero_fifa"]
            loc = pid_row["local"]
            vis = pid_row["visitante"]

            if current_num == num:
                print(f"  P{num} id={pid}: ya OK  ({loc} vs {vis})")
            else:
                await conn.execute(
                    "UPDATE partido SET numero_fifa = $1 WHERE id = $2",
                    num, pid
                )
                updated += 1
                marker = "ASIGNADO" if current_num is None else f"CORREGIDO (era {current_num})"
                print(f"  P{num} id={pid}: {marker}  ({loc} vs {vis})")

    print(f"\nTotal actualizados: {updated}")
    await conn.close()
    print("Listo. Ahora ejecutar validar_bracket_oficial.py")

if __name__ == "__main__":
    asyncio.run(main())
