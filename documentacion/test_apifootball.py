"""
Test de conexión con API-Football + listar ligas activas en 2026
Ejecutar: python "C:\proyecto FAST API\documentacion\test_apifootball.py"
"""
import urllib.request
import json

API_KEY  = "f13bee776659e2c20c715a81ecff2307"
API_BASE = "https://v3.football.api-sports.io"

LIGAS_SOPORTADAS = {1, 6, 9, 4, 2, 13}

headers = {"x-apisports-key": API_KEY}

def get(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k,v in params.items())
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

print("=== Estado de cuenta ===")
data = get("/status")
req = data.get("response", {}).get("requests", {})
print(f"Requests hoy: {req.get('current',0)} / {req.get('limit_day','?')}")

print("\n=== Ligas activas en 2026 (de las soportadas) ===")
data2 = get("/leagues", {"current": "true", "season": 2026})
ligas = data2.get("response", [])
for l in ligas:
    lid = l["league"]["id"]
    if lid in LIGAS_SOPORTADAS:
        season_info = l.get("seasons", [{}])[-1] if l.get("seasons") else {}
        print(f"  ✅ [{lid}] {l['league']['name']} — temporada {season_info.get('year','?')} — actual: {season_info.get('current','?')}")

print("\n=== Verificando temporadas disponibles para cada liga ===")
for lid in sorted(LIGAS_SOPORTADAS):
    d = get("/leagues", {"id": lid, "current": "true"})
    rs = d.get("response", [])
    if rs:
        seasons = rs[0].get("seasons", [])
        activas = [s for s in seasons if s.get("current")]
        for s in activas[-2:]:
            print(f"  [{lid}] {rs[0]['league']['name']} — season {s['year']} current={s['current']}")
    else:
        print(f"  [{lid}] sin datos activos")
