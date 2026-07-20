"""
fix_standings_grupo_g.py
========================
Recalcula los standings del Grupo G (Belgium, Egypt, Iran, New Zealand)
directamente desde los partidos ya correctos en la BD.
"""
import asyncio
import asyncpg
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_DSN    = "postgresql://app_user:superpassword@localhost:5432/becbuc"
BASE      = "http://localhost:8000"
TORNEO_ID = 2

GRUPO_G_NOMBRES = ["Belgium", "Egypt", "Iran", "New Zealand"]

async def main():
    conn = await asyncpg.connect(DB_DSN)

    # 1. Encontrar la fase del Grupo G
    fase = await conn.fetchrow("""
        SELECT f.id, f.nombre
        FROM fase f
        JOIN participacion pa ON pa.fase_id = f.id
        JOIN equipo e ON e.id = pa.equipo_id
        WHERE f.torneo_id = $1
          AND f.tipo ILIKE 'grupo%'
          AND e.nombre ILIKE ANY(ARRAY['%belgi%','%egypt%','%iran%','%new zealand%'])
        GROUP BY f.id, f.nombre
        HAVING COUNT(DISTINCT e.id) >= 3
        LIMIT 1
    """, TORNEO_ID)

    if not fase:
        print("ERROR: No se encontro la fase del Grupo G.")
        await conn.close()
        return

    fase_id = fase["id"]
    print(f"Fase: {fase['nombre']} (id={fase_id})\n")

    # 2. Cargar partidos del Grupo G
    partidos = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.goles_local, p.goles_visitante, p.estado,
               p.equipo_local_id, p.equipo_visitante_id,
               el.nombre AS local_nom, ev.nombre AS visit_nom
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.id = $1
        ORDER BY p.numero_fifa
    """, fase_id)

    print("Partidos base para calcular standings:")
    for p in partidos:
        gl = p["goles_local"]     if p["goles_local"]     is not None else "?"
        gv = p["goles_visitante"] if p["goles_visitante"] is not None else "?"
        print(f"  P{p['numero_fifa']:<3} {p['local_nom']:<22} {gl}-{gv} {p['visit_nom']:<22}  [{p['estado']}]")

    # 3. Calcular standings desde los partidos
    equipos_ids = await conn.fetch("""
        SELECT pa.equipo_id, e.nombre
        FROM participacion pa
        JOIN equipo e ON e.id = pa.equipo_id
        WHERE pa.fase_id = $1
    """, fase_id)

    stats = {}
    for eq in equipos_ids:
        stats[eq["equipo_id"]] = {
            "nombre": eq["nombre"],
            "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "pts": 0
        }

    for p in partidos:
        gl = p["goles_local"]
        gv = p["goles_visitante"]
        lid = p["equipo_local_id"]
        vid = p["equipo_visitante_id"]

        if gl is None or gv is None:
            continue
        if lid not in stats or vid not in stats:
            continue

        stats[lid]["pj"] += 1
        stats[vid]["pj"] += 1
        stats[lid]["gf"] += gl
        stats[lid]["gc"] += gv
        stats[vid]["gf"] += gv
        stats[vid]["gc"] += gl

        if gl > gv:
            stats[lid]["pg"] += 1; stats[lid]["pts"] += 3
            stats[vid]["pp"] += 1
        elif gl < gv:
            stats[vid]["pg"] += 1; stats[vid]["pts"] += 3
            stats[lid]["pp"] += 1
        else:
            stats[lid]["pe"] += 1; stats[lid]["pts"] += 1
            stats[vid]["pe"] += 1; stats[vid]["pts"] += 1

    # 4. Mostrar standings calculados
    sorted_stats = sorted(stats.values(), key=lambda s: (-s["pts"], -(s["gf"]-s["gc"]), -s["gf"]))
    print("\nStandings calculados (CORRECTO):")
    for i, s in enumerate(sorted_stats, 1):
        gd = s["gf"] - s["gc"]
        print(f"  {i}. {s['nombre']:<22} {s['pts']}pts  PJ={s['pj']} PG={s['pg']} PE={s['pe']} PP={s['pp']}  GF={s['gf']} GC={s['gc']} GD={gd:+d}")

    print("\nStandings actuales en BD (participacion):")
    current = await conn.fetch("""
        SELECT e.nombre, pa.pts, pa.pj, pa.pg, pa.pe, pa.pp, pa.gf, pa.gc, (pa.gf-pa.gc) AS gd, pa.equipo_id
        FROM participacion pa
        JOIN equipo e ON e.id = pa.equipo_id
        WHERE pa.fase_id = $1
        ORDER BY pa.pts DESC, (pa.gf-pa.gc) DESC, pa.gf DESC
    """, fase_id)

    for r in current:
        print(f"  {r['nombre']:<22} {r['pts']}pts  PJ={r['pj']} PG={r['pg']} PE={r['pe']} PP={r['pp']}  GF={r['gf']} GC={r['gc']} GD={r['gd']:+d}")

    # 5. Verificar si hay diferencias
    diferencias = False
    for eid, s in stats.items():
        cur = next((r for r in current if r["equipo_id"] == eid), None)
        if cur and (cur["pts"] != s["pts"] or cur["gf"] != s["gf"] or cur["gc"] != s["gc"]):
            diferencias = True
            break

    if not diferencias:
        print("\nOK: Los standings en BD ya son correctos.")
        await conn.close()
        return

    print("\nHay diferencias. Aplicar correcciones? (s/n): ", end="")
    confirm = input().strip().lower()
    if confirm != "s":
        print("Cancelado.")
        await conn.close()
        return

    # 6. Actualizar participacion
    async with conn.transaction():
        for eid, s in stats.items():
            gd = s["gf"] - s["gc"]
            await conn.execute("""
                UPDATE participacion
                SET pj=$1, pg=$2, pe=$3, pp=$4, gf=$5, gc=$6, pts=$7
                WHERE fase_id=$8 AND equipo_id=$9
            """, s["pj"], s["pg"], s["pe"], s["pp"], s["gf"], s["gc"], s["pts"],
                fase_id, eid)
            print(f"  OK {s['nombre']}: {s['pts']}pts  GF={s['gf']}  GC={s['gc']}")

    print("\nOK Standings actualizados.")

    # 7. Recalcular puntajes via API
    import urllib.request, json as _json
    try:
        req = urllib.request.Request(
            f"{BASE}/api/v1/auth/login",
            _json.dumps({"username": "jose", "password": "catalina"}).encode(),
            {"Content-Type": "application/json"},
        )
        token = _json.loads(urllib.request.urlopen(req, timeout=10).read())["access_token"]
        hdrs = {"Authorization": f"Bearer {token}"}
        r = urllib.request.Request(
            f"{BASE}/api/v1/bets/calcular-puntajes/{TORNEO_ID}", b"", hdrs, method="POST"
        )
        pts = _json.loads(urllib.request.urlopen(r, timeout=120).read())
        print(f"\nPuntajes recalculados: {pts.get('plenos', '?')} plenos")
    except Exception as e:
        print(f"\nWARN calcular puntajes: {e}")
        print("Ejecutalo manualmente desde el portal.")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
