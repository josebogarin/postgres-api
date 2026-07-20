"""
Diagnóstico: compara terceros en bracket-real vs mejores-terceros-provisorios.
Muestra qué partidos R32 tienen terceros y si coinciden con los calculados.
"""
import urllib.request, urllib.error, json

BASE = "http://localhost:8000"
TORNEO_ID = 2

def api(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")
        return {"error": body_txt}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

OUT = []
def log(msg=""):
    OUT.append(msg)
    print(msg)

log("=== DIAGNÓSTICO BRACKET TERCEROS ===\n")

# Login
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
tok = r.get("access_token") if s == 200 else None

# 1. Obtener mejores terceros provisorios
log("[1] Mejores terceros provisorios:")
r, s = api("GET", f"/api/v1/bets/mejores-terceros-provisorios/{TORNEO_ID}", token=tok)
terceros_prov = {}  # equipo_id -> info
grupos_top8 = []
if s == 200:
    clasificados = r.get("clasificados", [])
    eliminados = r.get("eliminados", [])
    log(f"  DENTRO (top 8):")
    for t in clasificados[:8]:
        nm = t.get("nombre_es") or t.get("nombre", "?")
        grp = t.get("grupo", "?")
        pts = t.get("pts", 0)
        gd = t.get("gd", 0)
        fp = t.get("fair_play_pts", 0)
        fifa = t.get("fifa_ranking", "?")
        pend = t.get("pendientes", 0)
        log(f"    Grupo {grp}: {nm} pts={pts} gd={gd:+d} fp={fp} fifa={fifa} pend={pend}")
        terceros_prov[t["equipo_id"]] = t
        grupos_top8.append(grp)
    if eliminados:
        log(f"  FUERA (4 eliminados):")
        for t in eliminados:
            nm = t.get("nombre_es") or t.get("nombre", "?")
            grp = t.get("grupo", "?")
            pts = t.get("pts", 0)
            gd = t.get("gd", 0)
            log(f"    Grupo {grp}: {nm} pts={pts} gd={gd:+d}")
    log(f"  Grupos top8: {sorted(grupos_top8)}")
    frozenkey = frozenset(grupos_top8)
    log(f"  frozenset clave: {frozenkey}")
else:
    log(f"  ERROR {s}: {r}")

# 2. Obtener bracket-real
log("\n[2] Bracket-real R32 (P73-P88):")
r2, s2 = api("GET", f"/api/v1/bets/bracket-real/{TORNEO_ID}")
r32_partidos = []
terceros_en_bracket = {}  # grupo slot -> equipo nombre
if s2 == 200:
    partidos = r2.get("partidos", [])
    r32 = sorted([p for p in partidos if 73 <= p.get("num", 0) <= 88], key=lambda x: x["num"])
    for p in r32:
        num = p.get("num")
        ln = (p.get("local") or {}).get("nombre", "TBD") or "TBD"
        vn = (p.get("visitante") or {}).get("nombre", "TBD") or "TBD"
        lid = (p.get("local") or {}).get("equipo_id")
        vid = (p.get("visitante") or {}).get("equipo_id")
        l_fp = lid in terceros_prov
        v_fp = vid in terceros_prov
        markers = ""
        if l_fp:
            markers += f" ← 3er de Grupo {terceros_prov[lid]['grupo']}"
        if v_fp:
            markers += f" ← 3er de Grupo {terceros_prov[vid]['grupo']}"
        log(f"  P{num}: {ln} vs {vn}{markers}")

    # Contar cuántos de los top-8 terceros están en el bracket
    log(f"\n[3] Verificación terceros en bracket:")
    found_in_bracket = set()
    for p in r32:
        for side in ["local", "visitante"]:
            eid = (p.get(side) or {}).get("equipo_id")
            if eid and eid in terceros_prov:
                nm = (p.get(side) or {}).get("nombre", "?") or "?"
                grp = terceros_prov[eid]["grupo"]
                found_in_bracket.add(grp)

    missing = set(grupos_top8) - found_in_bracket
    extra = found_in_bracket - set(grupos_top8)

    log(f"  Top 8 grupos provisorios: {sorted(grupos_top8)}")
    log(f"  Grupos con tercero en bracket: {sorted(found_in_bracket)}")
    if missing:
        log(f"  ❌ FALTAN en bracket: {sorted(missing)}")
    if extra:
        log(f"  ⚠️  EXTRA en bracket (no en top8): {sorted(extra)}")
    if not missing and not extra:
        log(f"  ✅ Los 8 terceros del bracket coinciden con provisorios!")
else:
    log(f"  ERROR {s2}: {r2}")

# 3. Verificar el TERCEROS_COMBINACIONES directamente en Python
log("\n[4] Verificar TERCEROS_COMBINACIONES para el frozenset actual:")
try:
    import sys
    sys.path.insert(0, r"C:\proyecto FAST API\backend")
    from app.services.bracket_service import TERCEROS_COMBINACIONES
    key = frozenset(grupos_top8)
    comb = TERCEROS_COMBINACIONES.get(key)
    if comb:
        vs_1A, vs_1B, vs_1D, vs_1E, vs_1G, vs_1I, vs_1K, vs_1L = comb
        log(f"  Combinación encontrada para {sorted(key)}:")
        log(f"  P79 (1ro A vs): 3er grupo {vs_1A}")
        log(f"  P85 (1ro B vs): 3er grupo {vs_1B}")
        log(f"  P81 (1ro D vs): 3er grupo {vs_1D}")
        log(f"  P74 (1ro E vs): 3er grupo {vs_1E}")
        log(f"  P82 (1ro G vs): 3er grupo {vs_1G}")
        log(f"  P77 (1ro I vs): 3er grupo {vs_1I}")
        log(f"  P87 (1ro K vs): 3er grupo {vs_1K}")
        log(f"  P80 (1ro L vs): 3er grupo {vs_1L}")
    else:
        log(f"  ❌ NO hay entrada en TERCEROS_COMBINACIONES para {sorted(key)}")
        log(f"  Total entradas disponibles: {len(TERCEROS_COMBINACIONES)}")
        # Mostrar las 5 más parecidas
        def set_diff(s): return len(s.symmetric_difference(key))
        similares = sorted(TERCEROS_COMBINACIONES.keys(), key=set_diff)[:5]
        log(f"  Más parecidas:")
        for s in similares:
            log(f"    {sorted(s)} (diff={set_diff(s)})")
except Exception as ex:
    log(f"  Error importando bracket_service: {ex}")

log("\n=== FIN ===")
with open("diag_bracket_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))
print("\nLOG: diag_bracket_log.txt")
input("Enter para cerrar...")
