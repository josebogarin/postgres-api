"""
test_api_football.py — Test directo de API-Football
Correr: python test_api_football.py
"""
import requests, json, sys

API_KEY  = "f13bee776659e2c20c715a81ecff2307"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS  = {
    "x-rapidapi-key":  API_KEY,
    "x-rapidapi-host": "v3.football.api-sports.io",
}

def sep(title): print(f"\n{'='*55}\n  {title}\n{'='*55}")

# ── 1. Quota ──────────────────────────────────────────────────
sep("1. QUOTA / STATUS")
try:
    r = requests.get(f"{BASE_URL}/status", headers=HEADERS, timeout=10)
    d = r.json()
    sub  = d.get("response", {}).get("subscription", {})
    reqs = d.get("response", {}).get("requests",     {})
    print(f"  Plan      : {sub.get('plan','?')}")
    print(f"  Calls hoy : {reqs.get('current','?')} / {reqs.get('limit_day','?')}")
    print(f"  Activa    : {sub.get('active','?')}")
except Exception as e:
    print(f"  ERROR: {e}"); sys.exit(1)

# ── 2. Partidos finalizados Copa Mundial 2026 ─────────────────
sep("2. FIXTURES FINALIZADOS  (league=1, season=2026)")
try:
    r = requests.get(f"{BASE_URL}/fixtures",
        headers=HEADERS, timeout=15,
        params={"league": 1, "season": 2026, "status": "FT-AET-PEN"})
    fixes = r.json().get("response", [])
    remaining = r.headers.get("x-ratelimit-requests-remaining","?")
    print(f"  Cuota restante: {remaining}")
    print(f"  Fixtures FT/AET/PEN encontrados: {len(fixes)}")
    for fx in fixes:
        t  = fx["teams"]
        g  = fx["goals"]
        fi = fx["fixture"]
        print(f"  [{fi['id']}]  {t['home']['name']:25s} {g['home']:>2} – {g['away']:<2}  {t['away']['name']:25s}  ({fi['date'][:10]})")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 3. Partidos en vivo ahora ─────────────────────────────────
sep("3. EN VIVO AHORA — Copa Mundial 2026 (league=1)")
try:
    r = requests.get(f"{BASE_URL}/fixtures",
        headers=HEADERS, timeout=15,
        params={"live": "all", "league": 1, "season": 2026})
    lives = r.json().get("response", [])
    print(f"  Partidos en vivo Copa Mundial: {len(lives)}")
    for fx in lives:
        t  = fx["teams"]
        g  = fx["goals"]
        fi = fx["fixture"]
        ev = fx.get("events", [])
        print(f"\n  [{fi['id']}]  {t['home']['name']} {g['home']} – {g['away']} {t['away']['name']}  {fi['status'].get('elapsed','?')}'  st={fi['status']['short']}")
        print(f"    Fecha UTC: {fi['date']}")
        print(f"    Goles home: {g['home']}  away: {g['away']}")
        # Estadísticas si hay
        for stat_blk in fx.get("statistics",[]):
            team_name = stat_blk["team"]["name"]
            for s in stat_blk["statistics"]:
                if s["type"] in ("Yellow Cards","Red Cards","Total Shots","Ball Possession"):
                    print(f"    {team_name:20s}  {s['type']:20s}: {s['value']}")
        # Eventos goles
        for ev in fx.get("events",[]):
            if ev.get("type") in ("Goal","Card"):
                print(f"    {ev.get('time',{}).get('elapsed','?'):>3}' {ev['type']:6s}  {ev.get('team',{}).get('name','?'):20s}  {ev.get('player',{}).get('name','?')}")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 4. Buscar México específicamente ─────────────────────────
sep("4. BUSCAR MEXICO (hoy, season=2026)")
try:
    r = requests.get(f"{BASE_URL}/fixtures",
        headers=HEADERS, timeout=15,
        params={"team": 16, "season": 2026})   # team 16 = Mexico en API-Football
    fixes = r.json().get("response", [])
    print(f"  Fixtures México encontrados: {len(fixes)}")
    for fx in fixes[:5]:
        t  = fx["teams"]
        g  = fx["goals"]
        fi = fx["fixture"]
        print(f"  [{fi['id']}]  {t['home']['name']:25s} {g['home']:>2} – {g['away']:<2}  {t['away']['name']:25s}  st={fi['status']['short']}  {fi['date'][:16]}")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 5. Equipos en API-Football que matchean con BD ──────────────
sep("5. EQUIPOS Copa Mundial 2026 (league=1, season=2026)")
try:
    r = requests.get(f"{BASE_URL}/teams",
        headers=HEADERS, timeout=15,
        params={"league": 1, "season": 2026})
    teams = r.json().get("response", [])
    print(f"  Total equipos: {len(teams)}")
    # Mostrar los primeros 10
    for t in teams[:10]:
        print(f"  [{t['team']['id']:5d}]  {t['team']['name']}")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 6. Detalle completo fixture 1489369 (México vs Sudáfrica) ──
sep("6. DETALLE COMPLETO  fixture=1489369")
try:
    r = requests.get(f"{BASE_URL}/fixtures",
        headers=HEADERS, timeout=15,
        params={"id": 1489369})
    fixes = r.json().get("response", [])
    if not fixes:
        print("  Sin datos")
    else:
        fx = fixes[0]
        fi = fx["fixture"]
        t  = fx["teams"]
        g  = fx["goals"]
        sc = fx.get("score", {})
        print(f"  Fixture ID : {fi['id']}")
        print(f"  Estado     : {fi['status']['short']} ({fi['status'].get('elapsed','?')}')")
        print(f"  Marcador   : {t['home']['name']} {g['home']} – {g['away']} {t['away']['name']}")
        print(f"  HT score   : {sc.get('halftime',{})}")
        print(f"  FT score   : {sc.get('fulltime',{})}")
        print(f"  ET score   : {sc.get('extratime',{})}")
        print(f"  Penales    : {sc.get('penalty',{})}")
        print(f"\n  EVENTOS:")
        for ev in fx.get("events", []):
            t_name = ev.get("team",{}).get("name","?")
            p_name = ev.get("player",{}).get("name","?")
            min_   = ev.get("time",{}).get("elapsed","?")
            etype  = ev.get("type","?")
            detail = ev.get("detail","")
            print(f"    {min_:>3}' [{t_name:20s}]  {etype:8s}  {detail:20s}  {p_name}")
        print(f"\n  ESTADÍSTICAS:")
        for blk in fx.get("statistics", []):
            print(f"  {blk['team']['name']}:")
            for s in blk["statistics"]:
                print(f"    {s['type']:30s}: {s['value']}")
        print(f"\n  EQUIPOS ID:")
        print(f"    Home: [{t['home']['id']}] {t['home']['name']}")
        print(f"    Away: [{t['away']['id']}] {t['away']['name']}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n✅ Test completo")
