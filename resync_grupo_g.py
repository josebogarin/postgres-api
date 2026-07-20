"""
resync_grupo_g.py
=================
Fuerza re-sync de los 3 partidos del Grupo G (Belgium, Egypt, Iran, New Zealand)
desde API-Football y recalcula puntajes.
"""
import asyncio
import asyncpg
import urllib.request
import json
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_DSN    = "postgresql://app_user:superpassword@localhost:5432/becbuc"
BASE      = "http://localhost:8000"
TORNEO_ID = 2

# Equipos del Grupo G (nombres tal como están en la BD)
GRUPO_G_EQUIPOS = ["Belgium", "Egypt", "Iran", "New Zealand"]

async def main():
    conn = await asyncpg.connect(DB_DSN)

    # 1. Encontrar los partidos del Grupo G
    print("=== Partidos del Grupo G en BD ===\n")
    rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.estado,
               p.goles_local, p.goles_visitante,
               p.api_fixture_id,
               p.amarillas, p.rojas, p.decisiones_var,
               el.nombre AS local_nom, ev.nombre AS visit_nom,
               f.nombre AS fase_nom
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1
          AND f.tipo ILIKE 'grupo%'
          AND (el.nombre = ANY($2) OR ev.nombre = ANY($2))
        ORDER BY p.numero_fifa
    """, TORNEO_ID, GRUPO_G_EQUIPOS)

    if not rows:
        # Intentar con nombres alternativos
        rows = await conn.fetch("""
            SELECT p.id, p.numero_fifa, p.estado,
                   p.goles_local, p.goles_visitante,
                   p.api_fixture_id,
                   el.nombre AS local_nom, ev.nombre AS visit_nom,
                   f.nombre AS fase_nom
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE f.torneo_id = $1 AND f.tipo ILIKE 'grupo%'
              AND (
                  el.nombre ILIKE '%belgi%' OR el.nombre ILIKE '%egypt%' OR
                  el.nombre ILIKE '%iran%'  OR el.nombre ILIKE '%new zealand%' OR
                  ev.nombre ILIKE '%belgi%' OR ev.nombre ILIKE '%egypt%' OR
                  ev.nombre ILIKE '%iran%'  OR ev.nombre ILIKE '%new zealand%'
              )
            ORDER BY p.numero_fifa
        """, TORNEO_ID)

    if not rows:
        print("ERROR: No se encontraron partidos del Grupo G en BD.")
        await conn.close()
        return

    print(f"Encontrados {len(rows)} partidos:\n")
    fixture_ids = []
    partido_ids = []
    for r in rows:
        gl = r['goles_local']  if r['goles_local']  is not None else '?'
        gv = r['goles_visitante'] if r['goles_visitante'] is not None else '?'
        fix = r['api_fixture_id'] or 'SIN MAPEAR'
        print(f"  P{r['numero_fifa']:<3} {r['local_nom']:<22} {gl}-{gv} {r['visit_nom']:<22}  [{r['estado']}]  api_fixture_id={fix}")
        if r['api_fixture_id']:
            fixture_ids.append(r['api_fixture_id'])
        partido_ids.append(r['id'])

    sin_mapear = [r for r in rows if not r['api_fixture_id']]
    if sin_mapear:
        print(f"\nAVISO: {len(sin_mapear)} partido(s) sin api_fixture_id. No se puede hacer sync automatico para esos.")

    await conn.close()

    if not fixture_ids:
        print("\nNinguno tiene api_fixture_id. Usa el sync general o cargalos manualmente.")
        return

    # 2. Login
    print("\n=== Conectando al API ===")
    try:
        req = urllib.request.Request(
            f"{BASE}/api/v1/auth/login",
            json.dumps({"username": "jose", "password": "catalina"}).encode(),
            {"Content-Type": "application/json"},
        )
        token = json.loads(urllib.request.urlopen(req, timeout=10).read())["access_token"]
        hdrs = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        print("  Login OK")
    except Exception as e:
        print(f"  ERROR login: {e}")
        return

    def api_post(path, timeout=120):
        r = urllib.request.Request(f"{BASE}{path}", b"", hdrs, method="POST")
        return json.loads(urllib.request.urlopen(r, timeout=timeout).read())

    # 3. Sync con force=true y max_detalle alto para cubrir los 6 partidos del grupo
    print(f"\n  Ejecutando sync forzado (max_detalle=72 para cubrir grupo completo)...")
    print("  Esto puede tardar hasta 60 segundos...")
    try:
        s = api_post(f"/api/v1/bets/sync-resultados/{TORNEO_ID}?force=true&max_detalle=72", timeout=120)
        act = s.get("actualizados", 0)
        print(f"  Sync OK: {act} partidos actualizados")
        if s.get("error"):
            print(f"  WARN: {s['error']}")
    except Exception as e:
        print(f"  ERROR sync: {e}")
        print("  Intentando con max_detalle menor...")
        try:
            s = api_post(f"/api/v1/bets/sync-resultados/{TORNEO_ID}?force=true&max_detalle=20", timeout=60)
            act = s.get("actualizados", 0)
            print(f"  Sync OK: {act} partidos actualizados")
        except Exception as e2:
            print(f"  ERROR: {e2}")
            return

    # 4. Recalcular puntajes
    print("\n  Recalculando puntajes...")
    try:
        pts = api_post(f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}", timeout=120)
        pl = pts.get("plenos", "?")
        print(f"  Puntajes OK: {pl} plenos")
    except Exception as e:
        print(f"  ERROR calcular puntajes: {e}")

    # 5. Mostrar standings actualizados del Grupo G
    conn2 = await asyncpg.connect(DB_DSN)
    print("\n=== Standings Grupo G (actualizado) ===\n")
    updated = await conn2.fetch("""
        SELECT p.id, p.numero_fifa, p.estado,
               p.goles_local, p.goles_visitante,
               el.nombre AS local_nom, ev.nombre AS visit_nom
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1
          AND f.tipo ILIKE 'grupo%'
          AND (
              el.nombre ILIKE '%belgi%' OR el.nombre ILIKE '%egypt%' OR
              el.nombre ILIKE '%iran%'  OR el.nombre ILIKE '%new zealand%' OR
              ev.nombre ILIKE '%belgi%' OR ev.nombre ILIKE '%egypt%' OR
              ev.nombre ILIKE '%iran%'  OR ev.nombre ILIKE '%new zealand%'
          )
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    for r in updated:
        gl = r['goles_local']     if r['goles_local']     is not None else '?'
        gv = r['goles_visitante'] if r['goles_visitante'] is not None else '?'
        print(f"  P{r['numero_fifa']:<3} {r['local_nom']:<22} {gl}-{gv} {r['visit_nom']:<22}  [{r['estado']}]")

    # Standings del grupo
    standings = await conn2.fetch("""
        SELECT e.nombre, pa.pts, pa.pj, pa.gf, pa.gc, (pa.gf - pa.gc) AS gd
        FROM participacion pa
        JOIN equipo e ON e.id = pa.equipo_id
        JOIN fase fa ON fa.id = pa.fase_id
        WHERE fa.torneo_id = $1 AND fa.tipo ILIKE 'grupo%'
          AND e.nombre ILIKE ANY(ARRAY['%belgi%','%egypt%','%iran%','%new zealand%'])
        ORDER BY pa.pts DESC, (pa.gf - pa.gc) DESC, pa.gf DESC
    """, TORNEO_ID)

    if standings:
        print("\n  TABLA:")
        for i, s in enumerate(standings, 1):
            print(f"  {i}. {s['nombre']:<22} {s['pts']}pts  PJ={s['pj']}  GD={s['gd']:+d}  GF={s['gf']}  GC={s['gc']}")

    await conn2.close()
    print("\nListo.")

if __name__ == "__main__":
    asyncio.run(main())
