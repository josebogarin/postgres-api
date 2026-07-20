"""
sync_ayer.py — Sincroniza partidos de ayer y recalcula puntajes.
Uso: python sync_ayer.py
     (requiere servidor uvicorn corriendo en localhost:8000)
"""
import json, urllib.request, urllib.parse, urllib.error, sys

BASE      = "http://localhost:8000/api/v1"
TORNEO_ID = 2

print("=" * 60)
print("  SYNC PARTIDOS DE AYER + RECALCULO PUNTAJES")
print("=" * 60)
print()

# ── 1. Login ──────────────────────────────────────────────────
print("1. Autenticando como jose...")
token = None
for ct, payload in [
    ("application/x-www-form-urlencoded",
     urllib.parse.urlencode({"username": "jose", "password": "catalina"}).encode()),
    ("application/json",
     json.dumps({"username": "jose", "password": "catalina"}).encode()),
]:
    try:
        req = urllib.request.Request(
            f"{BASE}/auth/login", data=payload,
            headers={"Content-Type": ct})
        with urllib.request.urlopen(req, timeout=10) as r:
            token = json.loads(r.read())["access_token"]
        print(f"   OK")
        break
    except urllib.error.HTTPError as e:
        print(f"   HTTP {e.code}: {e.read().decode()[:150]}")
    except Exception as e:
        print(f"   Error: {e}")

if not token:
    print("ERROR: no se pudo autenticar. ¿Está el servidor corriendo?")
    sys.exit(1)

# ── 2. Sync de ayer ───────────────────────────────────────────
print()
print("2. Sincronizando partidos de ayer...")
print("   (Flujo: API-Football → ESPN → SofaScore)")
try:
    req = urllib.request.Request(
        f"{BASE}/bets/sync-resultados/{TORNEO_ID}?resync_ayer=true",
        data=b"",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())

    print(f"   ok:            {data.get('ok')}")
    print(f"   actualizados:  {data.get('actualizados')}")
    print(f"   ya_finalizados:{len(data.get('ya_finalizados', []))}")
    print(f"   errores:       {data.get('errores')}")
    print(f"   api_calls:     {data.get('api_calls')}")

    espn = data.get("espn_correcciones", [])
    ss   = data.get("sofascore_correcciones", [])
    print(f"   ESPN correcciones:      {len(espn)}")
    print(f"   SofaScore correcciones: {len(ss)}")

    if espn:
        print()
        print("   [ESPN corregidos]")
        for c in espn:
            print(f"     partido {c['partido_id']}: {c['corr']}")

    if ss:
        print()
        print("   [SofaScore corregidos]")
        for c in ss:
            print(f"     partido {c['partido_id']}: {c['corr']}")

    if data.get("errores") and isinstance(data.get("ids_errores"), list):
        print()
        print("   [Errores]")
        for e in data["ids_errores"][:5]:
            print(f"     partido {e.get('partido_id')}: {e.get('error','')[:80]}")

    # Puntajes dentro del sync
    puntajes = data.get("puntajes", {})
    if puntajes:
        print()
        print(f"   Puntajes calculados OK: {puntajes.get('ok')}")
        print(f"   Procesados: {puntajes.get('procesados')}")

except urllib.error.HTTPError as e:
    body = e.read().decode()[:400]
    print(f"   ERROR HTTP {e.code}: {body}")
    sys.exit(1)
except Exception as e:
    print(f"   ERROR: {e}")
    sys.exit(1)

# ── 3. Recalcular puntajes ────────────────────────────────────
print()
print("3. Recalculando puntajes...")
try:
    req = urllib.request.Request(
        f"{BASE}/bets/calcular-puntajes/{TORNEO_ID}",
        data=b"",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        pts = json.loads(r.read())
    print(f"   Plenos:   {pts.get('plenos', '?')}")
    print(f"   Aciertos: {pts.get('aciertos', '?')}")
    print(f"   Globales: {pts.get('globales_procesadas', '?')}")
except Exception as e:
    print(f"   ERROR recalculando: {e}")

# ── 4. Top 10 ─────────────────────────────────────────────────
print()
print("4. Top 10 ranking:")
try:
    req = urllib.request.Request(
        f"{BASE}/bets/ranking/{TORNEO_ID}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rk = json.loads(r.read())
    lista = rk if isinstance(rk, list) else rk.get("ranking", [])
    for i, ap in enumerate(lista[:10], 1):
        nombre = ap.get("nombre") or ap.get("nombre_apostador") or ap.get("apostador", "?")
        pts    = ap.get("puntos_total", ap.get("total", ap.get("pts_total", "?")))
        print(f"   {i:>2}. {nombre:<35} {pts} pts")
except Exception as e:
    print(f"   ERROR ranking: {e}")

print()
print("Listo.")
