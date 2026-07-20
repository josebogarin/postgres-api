"""
Test de tabla.html y endpoints clave.
Ejecutar con el servidor activo: python test_tabla.py
"""
import requests, sys
from becbuc_config import BASE_URL, TORNEO_ID, ADMIN_USER, ADMIN_PASS

def ok(msg):   print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}")
def warn(msg): print(f"  ⚠️  {msg}")

# 1. Login
print(f"\n[1] Login ({ADMIN_USER})")
r = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"username": ADMIN_USER, "password": ADMIN_PASS})
if r.status_code != 200:
    fail(f"Login falló {r.status_code}: {r.text[:200]}"); sys.exit(1)
token = r.json()["access_token"]
ok("Token OK"); H = {"Authorization": f"Bearer {token}"}

# 2. tabla.html se sirve
print("\n[2] GET /tabla")
r = requests.get(f"{BASE_URL}/tabla")
if r.status_code == 200 and "dicSmartFill" in r.text:
    ok("tabla.html sirve correctamente")
else:
    fail(f"Status {r.status_code}")

# 3. /admin/db-tables app_db
print("\n[3] GET /admin/db-tables (app_db)")
r = requests.get(f"{BASE_URL}/api/v1/admin/db-tables", headers=H)
if r.status_code == 200:
    d = r.json()
    ok(f"tables={len(d.get('tables',[]))} views={len(d.get('views',[]))}")
else:
    fail(f"Status {r.status_code}: {r.text[:100]}")

# 4. /admin/db-tables becbuc
print("\n[4] GET /admin/db-tables?db_slug=becbuc")
r = requests.get(f"{BASE_URL}/api/v1/admin/db-tables?db_slug=becbuc", headers=H)
if r.status_code == 200:
    d = r.json()
    ok(f"tables={len(d.get('tables',[]))} views={len(d.get('views',[]))}")
else:
    fail(f"Status {r.status_code}: {r.text[:100]}")

# 5. Partidos del torneo activo (TORNEO_ID global)
print(f"\n[5] Partidos torneo_id={TORNEO_ID} ({['', 'Copa Mundo 2026'][TORNEO_ID==2]})")
r = requests.get(
    f"{BASE_URL}/api/v1/admin/tables/partido/rows"
    f"?limit=10&skip=0&db_slug=becbuc&filter_col=torneo_id&filter_val={TORNEO_ID}",
    headers=H
)
if r.status_code == 200:
    d = r.json(); rows = d.get("rows") or d.get("items") or []
    total = d.get("total", "?")
    ok(f"{total} partidos en total, mostrando {len(rows)}")
    for p in rows[:5]:
        estado = p.get("estado","?")
        gl = p.get("goles_local","?"); gv = p.get("goles_visitante","?")
        print(f"    partido_id={p.get('id')} estado={estado} goles={gl}-{gv}")
else:
    # Fallback: GET sin filtro y filtrar en Python
    r2 = requests.get(f"{BASE_URL}/api/v1/admin/tables/partido/rows?limit=200&skip=0&db_slug=becbuc", headers=H)
    if r2.status_code == 200:
        d = r2.json(); all_rows = d.get("rows") or d.get("items") or []
        rows = [p for p in all_rows if p.get("torneo_id") == TORNEO_ID]
        ok(f"{len(rows)} partidos torneo_id={TORNEO_ID} (filtrado en cliente)")
        for p in rows[:5]:
            print(f"    partido_id={p.get('id')} estado={p.get('estado','?')}")
    else:
        fail(f"Status {r.status_code}")

# 6. smart-fill-dic (POST)
print("\n[6] POST /admin/smart-fill-dic")
r = requests.post(
    f"{BASE_URL}/api/v1/admin/smart-fill-dic?table_name=partido&id_sistema=1&db_slug=becbuc",
    headers=H
)
if r.status_code == 200:
    d = r.json(); ok(f"total={d.get('total')} new={d.get('new')} changed={d.get('changed')}")
elif r.status_code == 405:
    fail("405 — fix POST no aplicado")
else:
    warn(f"Status {r.status_code}: {r.text[:100]}")

# 7. Ranking torneo activo
print(f"\n[7] GET /bets/ranking/{TORNEO_ID}")
r = requests.get(f"{BASE_URL}/api/v1/bets/ranking/{TORNEO_ID}", headers=H)
if r.status_code == 200:
    d = r.json(); rk = d if isinstance(d, list) else d.get("ranking", [])
    ok(f"{len(rk)} apostadores en ranking")
    for ap in rk[:3]:
        print(f"    {ap.get('nombre','?')}: {ap.get('puntos_total',0)} pts")
else:
    fail(f"Status {r.status_code}: {r.text[:100]}")

# 8. Confirmar GET smart-fill-dic da 405
print("\n[8] GET /admin/smart-fill-dic → debe dar 405")
r = requests.get(f"{BASE_URL}/api/v1/admin/smart-fill-dic?table_name=partido&id_sistema=1", headers=H)
if r.status_code == 405:
    ok("405 confirmado")
else:
    warn(f"Status {r.status_code}")

print(f"\n✅ Test completo (torneo_id={TORNEO_ID})\n")
