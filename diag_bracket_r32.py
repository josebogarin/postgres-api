"""
diag_bracket_r32.py
===================
Lee los partidos KO directo de la BD y muestra el estado del bracket R32.
Tambien verifica que bracket-real devuelva los datos correctos via API.
"""
import asyncio
import asyncpg
import urllib.request
import json

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
BASE   = "http://localhost:8000"
TORNEO_ID = 2

TIPO_LABEL = {
    "ronda32":       "R32 (16avos)",
    "ronda16":       "R16 (8avos)",
    "cuartos":       "Cuartos",
    "semis":         "Semis",
    "tercer_puesto": "3er Puesto",
    "final":         "Final",
}


async def main():
    conn = await asyncpg.connect(DB_DSN)

    print("=" * 70)
    print("DIAGNOSTICO BRACKET KO - BD directa")
    print("=" * 70)

    # 1. Verificar fases KO en BD
    fases = await conn.fetch("""
        SELECT id, tipo, nombre, orden, COALESCE(bloqueada, FALSE) AS bloqueada
        FROM fase
        WHERE torneo_id = $1 AND tipo <> 'grupo'
        ORDER BY orden, id
    """, TORNEO_ID)

    print(f"\n[Fases KO] {len(fases)} encontradas:")
    for f in fases:
        print(f"  id={f['id']} tipo={f['tipo']!r:<15} nombre={f['nombre']!r:<25} "
              f"orden={f['orden']} bloqueada={f['bloqueada']}")

    print()

    # 2. Partidos R32 (73-88) directo de BD usando f.torneo_id
    r32 = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.estado,
               p.goles_local, p.goles_visitante,
               p.penales_local, p.penales_visitante,
               p.torneo_id AS p_torneo_id,
               f.torneo_id AS f_torneo_id,
               f.tipo,
               COALESCE(el.nombre_es, el.nombre, 'TBD') AS local,
               COALESCE(ev.nombre_es, ev.nombre, 'TBD') AS visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1 AND p.numero_fifa BETWEEN 73 AND 88
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    print(f"[R32 via f.torneo_id] {len(r32)} partidos:")
    print(f"  {'#':<5} {'Local':<25} {'Visitante':<25} {'Estado':<12} p.tid  f.tid")
    print("  " + "-" * 80)
    for p in r32:
        gl = p['goles_local']
        gv = p['goles_visitante']
        score = f"{gl}-{gv}" if gl is not None else "---"
        print(f"  P{p['numero_fifa']:<3} {p['local']:<25} {p['visitante']:<25} "
              f"{(p['estado'] or 'N/A'):<12} {str(p['p_torneo_id']):<6} {str(p['f_torneo_id']):<6}")

    print()

    # 3. Verificar via p.torneo_id (para ver el bug original)
    r32_ptid = await conn.fetch("""
        SELECT COUNT(*) AS cnt
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE p.torneo_id = $1 AND f.tipo <> 'grupo'
    """, TORNEO_ID)
    cnt_ptid = r32_ptid[0]["cnt"]

    r32_ftid = await conn.fetch("""
        SELECT COUNT(*) AS cnt
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = $1 AND f.tipo <> 'grupo'
    """, TORNEO_ID)
    cnt_ftid = r32_ftid[0]["cnt"]

    print(f"[Comparacion filtro torneo_id]")
    print(f"  WHERE p.torneo_id = {TORNEO_ID}  →  {cnt_ptid} partidos KO")
    print(f"  WHERE f.torneo_id = {TORNEO_ID}  →  {cnt_ftid} partidos KO")
    if cnt_ptid == 0 and cnt_ftid > 0:
        print("  *** BUG CONFIRMADO: p.torneo_id es NULL en partidos KO ***")
        print("  *** FIX APLICADO: bracket_real ahora usa f.torneo_id ***")
    elif cnt_ptid == cnt_ftid:
        print("  OK: ambos filtros devuelven el mismo resultado")

    print()

    # 4. Verificar API bracket-real (si el servidor esta corriendo)
    print("[API bracket-real]")
    try:
        req = urllib.request.Request(
            f"{BASE}/api/v1/bets/bracket-real/{TORNEO_ID}",
            headers={"ngrok-skip-browser-warning": "true"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
        partidos = resp.get("partidos", [])
        r32_api = [p for p in partidos if p.get("tipo") == "ronda32"]
        print(f"  Total KO partidos retornados: {len(partidos)}")
        print(f"  R32 (tipo=ronda32): {len(r32_api)}")
        if len(r32_api) == 16:
            print("  ✅ API devuelve los 16 partidos R32 correctamente")
        elif len(r32_api) == 0:
            print("  ❌ API devuelve 0 partidos R32 — verificar fix en apostador_bets.py")
        else:
            print(f"  ⚠ API devuelve {len(r32_api)}/16 partidos R32")
        if r32_api:
            print()
            print("  Muestra primeros 4:")
            for p in r32_api[:4]:
                loc = (p.get("local") or {}).get("nombre", "TBD")
                vis = (p.get("visitante") or {}).get("nombre", "TBD")
                print(f"    P{p['num']}: {loc} vs {vis} [{p.get('finalizado') and 'FIN' or 'PEND'}]")
    except Exception as e:
        print(f"  ⚠ Servidor no responde: {e}")
        print("  Verificar que uvicorn esté corriendo en puerto 8000")

    await conn.close()
    print("\nListo.")


if __name__ == "__main__":
    asyncio.run(main())
