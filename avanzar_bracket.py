"""
Avanza bracket y verifica mejores terceros (sin sync API-Football).
"""
import urllib.request, urllib.error, json, sys

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
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read()), e.code
        except:
            return {"error": str(e)}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

print("=== AVANZAR BRACKET + MEJORES TERCEROS ===\n")

# 1. Login
print("[1/3] Login...")
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
if s != 200:
    print(f"  ERROR login: {s} {r}")
    input("Press Enter to exit...")
    sys.exit(1)
tok = r["access_token"]
print("  OK")

# 2. Avanzar bracket
print(f"\n[2/3] Avanzar bracket (torneo {TORNEO_ID})...")
r, s = api("POST", f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}", token=tok)
if s == 200:
    print(f"  OK - {r.get('mensaje', r)}")
else:
    print(f"  WARNING {s}: {r}")

# 3. Verificar mejores terceros
print(f"\n[3/3] Verificando mejores terceros...")
r, s = api("GET", f"/api/v1/bets/mejores-terceros-provisorios/{TORNEO_ID}", token=tok)
if s == 200:
    t3 = r.get("terceros", [])
    print(f"  grupos_completos={r.get('grupos_completos')}/{r.get('grupos_totales')}")
    print(f"\n  RANKING TERCEROS:")
    for t in t3:
        prov = " ⚡LIVE" if t.get("provisorio") else ""
        dentro = "✓" if t.get("dentro") else "✗"
        py_mark = " <-- PARAGUAY" if "Para" in t.get("nombre","") else ""
        print(f"  [{t['rank']}]{dentro} Grupo {t['grupo']} {t['nombre']:<28} pts={t.get('pts',0)} gd={t.get('gd',0):+d} gf={t.get('gf',0)} pj={t.get('pj',0)}{prov}{py_mark}")
    corte = r.get("corte_pts")
    margen = r.get("margen")
    if corte is not None:
        print(f"\n  Corte: {corte} pts  |  Margen 8°/9°: {margen} pts")
else:
    print(f"  ERROR {s}: {r}")

print("\n=== LISTO ===")
input("\nPress Enter para cerrar...")
