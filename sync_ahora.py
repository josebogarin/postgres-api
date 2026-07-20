"""
sync_ahora.py — Auto-mapea fixtures/equipos y sincroniza resultados AHORA
Correr: python sync_ahora.py
"""
import requests, json, sys

BASE    = "http://localhost:8000"
USER    = "admin"
PASS    = "faute"

s = requests.Session()

# ── 1. Login ─────────────────────────────────────────────────
print("🔐 Login...")
r = s.post(f"{BASE}/api/v1/auth/login", json={"username": USER, "password": PASS}, timeout=10)
if r.status_code == 401:
    # Algunos setups usan form data en vez de JSON
    r = s.post(f"{BASE}/api/v1/auth/login",
               data={"username": USER, "password": PASS},
               headers={"Content-Type": "application/x-www-form-urlencoded"},
               timeout=10)
r.raise_for_status()
data = r.json()
token = data.get("access_token") or data.get("token")
if not token:
    print(f"   ❌ No se encontró token en respuesta: {data}")
    sys.exit(1)
s.headers["Authorization"] = f"Bearer {token}"
print("   OK")

# ── 2. Obtener torneos activos ────────────────────────────────
print("\n📋 Torneos activos...")
torneos = s.get(f"{BASE}/api/v1/torneo/activas", timeout=10).json()
if not torneos:
    print("   ❌ No hay torneos activos")
    sys.exit(1)
for t in torneos:
    print(f"   [{t['id']}] {t.get('nombre','?')}  api_season={t.get('api_season','?')}")
torneo_id = torneos[0]["id"]
print(f"   → Usando torneo_id={torneo_id}")

# ── 3. Auto-mapeo (liga + equipos + fixtures) ─────────────────
print(f"\n🔗 Auto-mapeo (torneo {torneo_id})...")
r = s.post(f"{BASE}/api/v1/bets/api-mapeo/{torneo_id}/auto", timeout=60)
try:
    d = r.json()
    if r.status_code == 200:
        print(f"   ✓ Equipos mapeados  : {d.get('equipos_mapeados',0)}")
        print(f"   ✓ Partidos mapeados : {d.get('partidos_mapeados',0)}")
        print(f"   ✓ Equipos nuevos    : {d.get('equipos_nuevos',0)}")
        print(f"   ✓ Partidos nuevos   : {d.get('partidos_nuevos',0)}")
    else:
        print(f"   ⚠️ HTTP {r.status_code}: {json.dumps(d)[:400]}")
except Exception as e:
    print(f"   ⚠️ Error parseando respuesta: {e}")
    print(f"   Raw: {r.text[:400]}")

# ── 4. Sync desde API-Football ────────────────────────────────
print(f"\n⬇️  Sync resultados (torneo {torneo_id})...")
r = s.post(f"{BASE}/api/v1/bets/sync-resultados/{torneo_id}?max_detalle=10", timeout=90)
try:
    d = r.json()
    if r.status_code == 200:
        sync = d.get('sync', d)  # compat: puede estar en raíz o en 'sync'
        print(f"   ✓ Actualizados      : {d.get('actualizados', sync.get('actualizados','?'))}")
        print(f"   ✓ API calls         : {sync.get('api_calls','?')}")
        print(f"   ✓ Sin match API     : {sync.get('sin_match_api','?')}")
        print(f"   ✓ Ya finalizados    : {sync.get('ya_finalizados','?')}")
        print(f"   ✓ Errores           : {sync.get('errores','?')}")
        print(f"   ✓ Bracket OK        : {d.get('bracket_ok','?')}")
        print(f"   ✓ Puntajes OK       : {d.get('puntajes_ok','?')}")
        if sync.get('ids_actualizados'):
            print(f"   ✓ IDs actualizados  : {sync['ids_actualizados']}")
        if sync.get('ids_errores'):
            print(f"   ⚠️  Errores detalle  : {sync['ids_errores']}")
        if sync.get('auto_mapeo'):
            am = sync['auto_mapeo']
            print(f"   🔗 Auto-mapeo corrió: {am.get('equipos_mapeados',0)} eq / {am.get('partidos_mapeados',0)} fix")
        if sync.get('error'):
            print(f"   ⚠️  Error            : {sync['error']}")
        if d.get('puntajes'):
            p = d['puntajes']
            print(f"   ✓ Plenos            : {p.get('plenos',0)}")
            print(f"   ✓ Aciertos          : {p.get('aciertos',0)}")
    else:
        print(f"   ❌ HTTP {r.status_code}: {json.dumps(d)[:400]}")
except Exception as e:
    print(f"   ⚠️ Error: {e}\n   Raw: {r.text[:400]}")

# ── 5. Verificar partido México en BD ─────────────────────────
print(f"\n🔍 Partidos en vivo / hoy en BD...")
r = s.get(f"{BASE}/api/v1/bets/partidos-en-vivo/{torneo_id}", timeout=10)
try:
    d = r.json()
    ps = d.get("partidos", [])
    print(f"   Total: {len(ps)}")
    for p in ps:
        gl = p.get('goles_local')
        gv = p.get('goles_visitante')
        print(f"   {p.get('local_nombre','?'):25s} {gl if gl is not None else '?'} – {gv if gv is not None else '?'}  {p.get('visitante_nombre','?'):25s}  estado={p.get('estado','?')}")
except Exception as e:
    print(f"   Error: {e}")

# ── 6. Verificar estado BD directamente ──────────────────────────────────
print(f"\n🗄️  Estado BD (vía admin db-tables)...")
# Verificar competicion api_league_id para torneo 2
r = s.get(f"{BASE}/api/v1/admin/list_rows/competicion", timeout=10)
try:
    rows = r.json()
    for row in (rows if isinstance(rows, list) else rows.get("rows", [])):
        print(f"   comp [{row.get('id')}] {row.get('nombre','?'):30s}  api_league_id={row.get('api_league_id')}")
except Exception as e:
    print(f"   (no disponible: {e})")

# Verificar partido Mexico vs SA
r = s.get(f"{BASE}/api/v1/bets/grupos/{torneo_id}", timeout=15)
try:
    d = r.json()
    grupos = d if isinstance(d, list) else d.get("grupos", [])
    for g in grupos:
        for p in g.get("partidos", []):
            local = p.get("equipo_local", {}).get("nombre", "") or p.get("local_nombre", "")
            visit = p.get("equipo_visitante", {}).get("nombre", "") or p.get("visitante_nombre", "")
            fix_id = p.get("api_fixture_id")
            estado = p.get("estado", "?")
            if "mexico" in local.lower() or "mexico" in visit.lower() or "south africa" in local.lower() or "south africa" in visit.lower():
                print(f"   PARTIDO: {local} vs {visit}  api_fixture_id={fix_id}  estado={estado}  goles={p.get('goles_local')}-{p.get('goles_visitante')}")
except Exception as e:
    print(f"   (error grupos: {e})")

print("\n✅ Listo")
