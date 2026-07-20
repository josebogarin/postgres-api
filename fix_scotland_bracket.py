"""
Fix bracket: avanzar-bracket con nuevo sort_unified=True
Verifica que Scotland NO aparezca en R32.
"""
import urllib.request, urllib.error, json, sys

BASE = "http://localhost:8000"
TORNEO_ID = 2
OUT = []

def log(msg=""):
    OUT.append(msg)
    print(msg)

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
        try:
            body_txt = e.read().decode(errors="replace")
            return {"error": body_txt}, e.code
        except:
            return {"error": str(e)}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

log("=== FIX BRACKET SCOTLAND ===")

# 1. Login
log("\n[1] Login...")
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
if s != 200:
    log(f"  ERROR login: {s} {r}")
    sys.exit(1)
tok = r["access_token"]
log("  OK")

# 2. Avanzar bracket (aplica el nuevo sort_unified=True)
log(f"\n[2] POST /avanzar-bracket/{TORNEO_ID}...")
r, s = api("POST", f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}", token=tok)
if s == 200:
    log(f"  OK: {r.get('mensaje', r)}")
else:
    log(f"  ERROR {s}: {r}")

# 3. Verificar bracket-real
log(f"\n[3] GET /bracket-real/{TORNEO_ID}...")
r, s = api("GET", f"/api/v1/bets/bracket-real/{TORNEO_ID}")
if s == 200:
    partidos = r.get("partidos", [])
    r32 = [p for p in partidos if 73 <= p.get("num", 0) <= 88]
    log(f"  {len(r32)} partidos R32:")
    scotland_encontrado = False
    for p in sorted(r32, key=lambda x: x.get("num", 0)):
        ln = p.get("local", {}).get("nombre", "TBD") if p.get("local") else "TBD"
        vn = p.get("visitante", {}).get("nombre", "TBD") if p.get("visitante") else "TBD"
        flag = "  ❌ SCOTLAND!" if "scotland" in (ln+vn).lower() or "escocia" in (ln+vn).lower() else ""
        if flag:
            scotland_encontrado = True
        log(f"    P{p['num']:>3}: {ln} vs {vn}{flag}")
    if not scotland_encontrado:
        log("\n  ✅ Scotland NO está en el bracket R32!")
    else:
        log("\n  ❌ Scotland TODAVÍA está en el bracket!")
else:
    log(f"  ERROR {s}: {r}")

# 4. Verificar mejores terceros provisorios
log(f"\n[4] GET /mejores-terceros-provisorios/{TORNEO_ID}...")
r, s = api("GET", f"/api/v1/bets/mejores-terceros-provisorios/{TORNEO_ID}", token=tok)
if s == 200:
    terceros = r.get("terceros", [])
    log(f"  Top 8 mejores terceros:")
    for i, t in enumerate(terceros[:8]):
        grp = t.get("grupo", "?")
        nm = t.get("nombre_es") or t.get("nombre", "?")
        pts = t.get("pts", 0)
        gd = t.get("gd", 0)
        pend = t.get("pendientes", 0)
        log(f"    [{i+1}] Grupo {grp}: {nm} pts={pts} gd={gd:+d} pend={pend}")
else:
    log(f"  ERROR {s}: {r}")

log("\n=== FIN ===")
with open("fix_scotland_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))
print("\nLOG: fix_scotland_log.txt")
input("Enter para cerrar...")
