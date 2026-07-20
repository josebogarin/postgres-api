"""
Recalculo completo: sync -> puntajes -> bracket
Doble click para correr (usa el venv del backend)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import urllib.request, urllib.error, json, time

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
        body_err = e.read()
        try:
            return json.loads(body_err), e.code
        except:
            return {"error": body_err.decode(errors="replace")}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

print("=== RECALCULO BECBUC ===")
print()

# 1. Login
print("[1/5] Login...")
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
if s != 200:
    print(f"  ERROR login: {s} {r}")
    input("Press Enter to exit...")
    sys.exit(1)
tok = r["access_token"]
print(f"  OK")

# 2. Sync desde API-Football (trae resultados de hoy)
print(f"\n[2/5] Sync API-Football (torneo {TORNEO_ID})...")
r, s = api("POST", f"/api/v1/bets/sync-resultados/{TORNEO_ID}?force=true&max_detalle=20", token=tok)
if s == 200:
    print(f"  OK - actualizados={r.get('actualizados',0)} bracket={r.get('bracket_ok')} puntajes={r.get('puntajes_ok')}")
else:
    print(f"  WARNING {s}: {r}")

# 3. Avanzar bracket
print(f"\n[3/5] Avanzar bracket...")
r, s = api("POST", f"/api/v1/bets/avanzar-bracket/{TORNEO_ID}", token=tok)
if s == 200:
    print(f"  OK - {r}")
else:
    print(f"  WARNING {s}: {r}")

# 4. Calcular puntajes
print(f"\n[4/5] Calcular puntajes...")
r, s = api("POST", f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}", token=tok)
if s == 200:
    print(f"  OK - procesados={r.get('puntajes_procesados',0)} globales={r.get('globales_procesadas',0)}")
else:
    print(f"  WARNING {s}: {r}")

# 5. Verificar mejores terceros
print(f"\n[5/5] Verificando mejores terceros...")
r, s = api("GET", f"/api/v1/bets/mejores-terceros-provisorios/{TORNEO_ID}", token=tok)
if s == 200:
    t3 = r.get("terceros", [])
    print(f"  OK - {len(t3)} terceros, grupos_completos={r.get('grupos_completos')}/{r.get('grupos_totales')}")
    print(f"\n  RANKING TERCEROS:")
    for t in t3:
        prov = " ⚡LIVE" if t.get("provisorio") else ""
        dentro = "✓" if t.get("dentro") else "✗"
        print(f"  [{t['rank']}]{dentro} Grupo {t['grupo']} {t['nombre']:<20} pts={t.get('pts',0)} gd={t.get('gd',0)} gf={t.get('gf',0)} pj={t.get('pj',0)}{prov}")
    corte = r.get("corte_pts")
    margen = r.get("margen")
    if corte is not None:
        print(f"\n  Corte: {corte} pts  |  Margen 8°/9°: {margen} pts")
else:
    print(f"  ERROR {s}: {r}")

print("\n=== LISTO ===")
input("\nPress Enter para cerrar...")
