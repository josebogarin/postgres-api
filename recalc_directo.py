"""
Recalcula mejores terceros y avanza bracket R32 directamente via DB.
No requiere uvicorn corriendo. Conecta a PostgreSQL Docker directamente.
Output: recalc_log.txt
"""
import asyncio, sys, json
from datetime import datetime

LOG = open("recalc_log.txt", "w", encoding="utf-8")

def log(msg=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()

TORNEO_ID = 2

async def main():
    try:
        import asyncpg
    except ImportError:
        log("ERROR: asyncpg no instalado. Instalar con: pip install asyncpg")
        return

    log("=== Recalc Mejores Terceros (directo a DB) ===")

    # Conectar a PostgreSQL Docker
    try:
        conn = await asyncpg.connect(
            host="localhost", port=5432,
            user="app_user", password="app_user",
            database="becbuc"
        )
        log("✓ Conectado a PostgreSQL")
    except Exception as e:
        log(f"ERROR conectando DB: {e}")
        log("Intentando con password vacío...")
        try:
            conn = await asyncpg.connect(
                host="localhost", port=5432,
                user="app_user", password="",
                database="becbuc"
            )
            log("✓ Conectado a PostgreSQL (sin password)")
        except Exception as e2:
            log(f"ERROR: {e2}")
            return

    try:
        await _recalc(conn)
    finally:
        await conn.close()
        log("Conexión cerrada.")

async def _recalc(conn):
    # 1. Asegurar columnas de fair play
    log("\n[1/5] Verificando columnas fair play...")
    for sql in [
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS local_amarillas INT",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS visitante_amarillas INT",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS local_rojas INT",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS visitante_rojas INT",
        "ALTER TABLE participacion ADD COLUMN IF NOT EXISTS fair_play_pts INT DEFAULT 0",
    ]:
        try:
            await conn.execute(sql)
        except Exception:
            pass
    log("  ✓ Columnas OK")

    # 2. Leer grupos y standings
    log("\n[2/5] Leyendo standings de grupos...")
    fases = await conn.fetch("""
        SELECT id, nombre FROM fase
        WHERE torneo_id=$1 AND tipo='grupo' AND nombre NOT ILIKE '%mejores%'
        ORDER BY nombre
    """, TORNEO_ID)

    standings = {}  # letra -> {equipos: [...]}
    for fase in fases:
        fid = fase["id"]
        letra = fase["nombre"].replace("Grupo ", "").replace("Group ", "").strip()

        equipos_r = await conn.fetch("""
            SELECT e.id AS equipo_id,
                   COALESCE(e.nombre_es, e.nombre) AS nombre,
                   e.fifa_ranking,
                   pa.pj, pa.pts, pa.gf, pa.gc, pa.posicion,
                   COALESCE(pa.fair_play_pts, 0) AS fair_play_pts
            FROM participacion pa
            JOIN equipo e ON e.id = pa.equipo_id
            WHERE pa.fase_id=$1
            ORDER BY pa.posicion ASC, pa.pts DESC
        """, fid)

        if not equipos_r:
            continue

        # Recalcular desde partidos reales
        eq_map = {r["equipo_id"]: {
            "equipo_id": r["equipo_id"], "nombre": r["nombre"],
            "fifa_ranking": r["fifa_ranking"] or 9999,
            "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "gd": 0, "pts": 0,
            "fair_play_pts": 0,
        } for r in equipos_r}

        partidos = await conn.fetch("""
            SELECT equipo_local_id AS lid, equipo_visitante_id AS vid,
                   goles_local AS gl, goles_visitante AS gv,
                   COALESCE(local_amarillas,0) AS la,
                   COALESCE(visitante_amarillas,0) AS va,
                   COALESCE(local_rojas,0) AS lr,
                   COALESCE(visitante_rojas,0) AS vr
            FROM partido
            WHERE fase_id=$1 AND estado='finalizado'
              AND goles_local IS NOT NULL AND goles_visitante IS NOT NULL
        """, fid)

        for p in partidos:
            lid, vid, gl, gv = p["lid"], p["vid"], p["gl"], p["gv"]
            la, va, lr, vr = p["la"], p["va"], p["lr"], p["vr"]
            if lid not in eq_map or vid not in eq_map:
                continue
            loc = eq_map[lid]; vis = eq_map[vid]
            loc["pj"] += 1; vis["pj"] += 1
            loc["gf"] += gl; vis["gf"] += gv
            loc["gc"] += gv; vis["gc"] += gl
            loc["gd"] += gl - gv; vis["gd"] += gv - gl
            if gl > gv:
                loc["pg"] += 1; loc["pts"] += 3; vis["pp"] += 1
            elif gl == gv:
                loc["pe"] += 1; loc["pts"] += 1; vis["pe"] += 1; vis["pts"] += 1
            else:
                vis["pg"] += 1; vis["pts"] += 3; loc["pp"] += 1
            loc["fair_play_pts"] += la + lr * 3
            vis["fair_play_pts"] += va + vr * 3

        # Ordenar: pts → DG → GF → fair_play_pts → fifa_ranking → nombre
        sorted_teams = sorted(eq_map.values(), key=lambda e: (
            -e["pts"], -e["gd"], -e["gf"],
            e["fair_play_pts"], e["fifa_ranking"], e["nombre"]
        ))
        for i, eq in enumerate(sorted_teams):
            eq["pos"] = i + 1
            eq["grupo"] = letra

        standings[letra] = {"fase_id": fid, "equipos": sorted_teams}

    log(f"  ✓ {len(standings)} grupos cargados")

    # 3. Actualizar participacion con fair_play_pts
    log("\n[3/5] Actualizando participacion.fair_play_pts...")
    updated = 0
    for grupo in standings.values():
        fid = grupo["fase_id"]
        for eq in grupo["equipos"]:
            await conn.execute("""
                UPDATE participacion
                SET pj=$1, pts=$2, gf=$3, gc=$4, posicion=$5, fair_play_pts=$6
                WHERE fase_id=$7 AND equipo_id=$8
            """, eq["pj"], eq["pts"], eq["gf"], eq["gc"],
               eq["pos"], eq["fair_play_pts"], fid, eq["equipo_id"])
            updated += 1
    log(f"  ✓ {updated} filas actualizadas")

    # 4. Seleccionar mejores 8 terceros (criterio FIFA: solo grupos completos)
    log("\n[4/5] Seleccionando mejores terceros (criterio FIFA)...")
    terceros_completos = []
    terceros_incompletos = []

    for letra, grupo in sorted(standings.items()):
        eqs = grupo["equipos"]
        if len(eqs) < 3:
            continue
        pj_esperado = len(eqs) - 1
        pj_min = min(e["pj"] for e in eqs)
        tercero = {**eqs[2], "grupo": letra}
        if pj_min >= pj_esperado:
            terceros_completos.append(tercero)
        else:
            terceros_incompletos.append(tercero)

    key_fn = lambda e: (-e["pts"], -e["gd"], -e["gf"],
                        e["fair_play_pts"], e["fifa_ranking"], e["grupo"])
    terceros_completos.sort(key=key_fn)
    terceros_incompletos.sort(key=key_fn)

    # Si hay menos de 8 completos, complementar con incompletos
    if len(terceros_completos) < 8 and terceros_incompletos:
        faltantes = 8 - len(terceros_completos)
        terceros_completos.extend(terceros_incompletos[:faltantes])
        terceros_incompletos = terceros_incompletos[faltantes:]

    clasificados = terceros_completos[:8]
    eliminados = (terceros_completos[8:] + terceros_incompletos)

    log(f"  Grupos con todos los partidos completados: {len([g for g in standings.values() if min(e['pj'] for e in g['equipos']) >= len(g['equipos'])-1])}/{len(standings)}")
    log(f"\n  CLASIFICADOS (mejores 8):")
    for t in clasificados:
        log(f"    [{t['grupo']}] {t['nombre']:<25} Pts:{t['pts']:2} DG:{t['gd']:+3} GF:{t['gf']:2} FP:{t['fair_play_pts']} PJ:{t['pj']}")
    if eliminados:
        log(f"\n  ELIMINADOS:")
        for t in eliminados:
            log(f"    [{t['grupo']}] {t['nombre']:<25} Pts:{t['pts']:2} DG:{t['gd']:+3} GF:{t['gf']:2} FP:{t['fair_play_pts']} PJ:{t['pj']}")

    # 5. Actualizar partidos R32 con los clasificados
    log("\n[5/5] Actualizando bracket R32...")
    # Leer partidos R32 (nums 73-88) ordenados por numero_fifa
    r32 = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.equipo_local_id, p.equipo_visitante_id,
               f.tipo
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE p.torneo_id=$1 AND f.tipo='ronda32'
        ORDER BY p.numero_fifa ASC
    """, TORNEO_ID)
    log(f"  Partidos R32 encontrados: {len(r32)}")
    if r32:
        log(f"  (Actualización R32 requiere la lógica completa de armar_ronda32 — pendiente vía API)")

    log("\n=== RECALCULO COMPLETADO ===")
    LOG.close()

if __name__ == "__main__":
    asyncio.run(main())
    input("\nPresioná Enter para cerrar...")
