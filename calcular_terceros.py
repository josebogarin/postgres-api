import urllib.request, urllib.error, json, sys

BASE = "http://localhost:8000"
TORNEO_ID = 2

def api(method, path, body=None, token=None, timeout=60):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        try:    return json.loads(e.read()), e.code
        except: return {"error": str(e)}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

# Login
r, s = api("POST", "/api/v1/auth/login", {"username":"jose","password":"catalina"}, timeout=15)
if s != 200: print("ERROR login"); input(); sys.exit(1)
tok = r["access_token"]

# Avanzar bracket (incluye seleccionar_mejores_terceros)
print("Avanzando bracket + seleccionando mejores terceros...")
r, s = api("POST", f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}", token=tok)
print(f"  HTTP {s}: {r}")

# Mostrar ranking mejores terceros
print("\nRanking mejores terceros (provisional):")
r, s = api("GET", f"/api/v1/bets/mejores-terceros-provisorios/{TORNEO_ID}", token=tok)
if s != 200:
    print(f"  ERROR {s}: {r}"); input(); sys.exit(1)

t3 = r.get("terceros", [])
print(f"  {r.get('grupos_completos')}/{r.get('grupos_totales')} grupos completos")
print(f"  Corte: {r.get('corte_pts')} pts  |  Margen: {r.get('margen')} pts\n")
for t in t3:
    mk  = "✓ DENTRO" if t.get("dentro") else "✗ FUERA "
    pv  = " ⚡LIVE" if t.get("provisorio") else ""
    fp  = t.get("fair_play_pts", 0)
    print(f"  [{t['rank']}] {mk} Grp {t['grupo']}  {t['nombre']:<25}  "
          f"pts={t.get('pts',0)}  gd={t.get('gd',0):+}  gf={t.get('gf',0)}  "
          f"pj={t.get('pj',0)}  fp={fp}{pv}")

print("\nLISTO")
input("Enter para cerrar...")
