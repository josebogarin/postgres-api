"""
Diagnóstico: prueba /mi-bracket y /bracket-real y guarda el resultado.
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

log("=== DIAGNOSTICO BRACKET ===")

# 1. Login
log("\n[1] Login...")
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
if s != 200:
    log(f"  ERROR login: {s}")
    with open("diag_bracket_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(OUT))
    input("Enter para salir...")
    sys.exit(1)
tok = r["access_token"]
log("  OK")

# 2. bracket-real (sin auth)
log(f"\n[2] GET /bracket-real/{TORNEO_ID}...")
r, s = api("GET", f"/api/v1/bets/bracket-real/{TORNEO_ID}")
if s == 200:
    partidos = r.get("partidos", [])
    log(f"  OK - {len(partidos)} partidos KO")
    tbd = sum(1 for p in partidos if not p.get("local") or not p.get("visitante"))
    log(f"  TBD (sin equipo): {tbd} de {len(partidos)}")
    # Mostrar R32
    r32 = [p for p in partidos if 73 <= p.get("num",0) <= 88]
    for p in r32:
        ln = p.get("local",{}).get("nombre","TBD") if p.get("local") else "TBD"
        vn = p.get("visitante",{}).get("nombre","TBD") if p.get("visitante") else "TBD"
        log(f"    P{p['num']:>3}: {ln} vs {vn} ({p.get('estado','?')})")
else:
    log(f"  ERROR {s}: {r}")

# 3. mi-bracket (con auth, usando apostador_id=9)
log(f"\n[3] GET /mi-bracket/{TORNEO_ID} (como jose)...")
r, s = api("GET", f"/api/v1/bets/mi-bracket/{TORNEO_ID}", token=tok)
if s == 200:
    ko = r.get("ko_bracket", [])
    mejores = r.get("mejores_terceros", [])
    log(f"  OK - ko_bracket={len(ko)} partidos, mejores_terceros={len(mejores)}")
else:
    log(f"  ERROR {s}:")
    err = r.get("error","") if isinstance(r, dict) else str(r)
    # Si es JSON de FastAPI
    if isinstance(r, dict) and "detail" in r:
        log(f"  detail: {r['detail']}")
    else:
        log(f"  {err[:500]}")

# 4. Probar con apostador_id=9 (primer apostador)
log(f"\n[4] GET /mi-bracket/{TORNEO_ID}?for_apostador_id=9 (como admin)...")
r, s = api("GET", f"/api/v1/bets/mi-bracket/{TORNEO_ID}?for_apostador_id=9", token=tok)
if s == 200:
    ko = r.get("ko_bracket", [])
    mejores = r.get("mejores_terceros", [])
    log(f"  OK - ko_bracket={len(ko)} partidos, mejores_terceros={len(mejores)}")
else:
    log(f"  ERROR {s}:")
    if isinstance(r, dict) and "detail" in r:
        log(f"  detail: {r['detail']}")
    else:
        log(f"  {str(r)[:500]}")

log("\n=== FIN ===")

with open("diag_bracket_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))
print("\nLOG: diag_bracket_log.txt")
input("Enter para cerrar...")
