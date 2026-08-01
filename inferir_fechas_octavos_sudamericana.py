# -*- coding: utf-8 -*-
"""
inferir_fechas_octavos_sudamericana.py

PROBLEMA: los 8 partidos de OCTAVOS de la Copa Sudamericana (torneo 14) se
sembraron a mano (poblar_octavos_sudamericana.py) con:
  - un INSERT que NO incluye 'fecha'  -> partido.fecha = NULL
  - el rival como placeholder "Gan. X/Y" (equipo ficticio, sin api_team_id)

Por eso el auto-mapeo de API-Football NUNCA les asigna fecha: _match_fixtures()
exige que AMBOS equipos sean reales (home_id y away_id). Con un rival placeholder
no hay match -> no hay api_fixture_id -> no se infiere la fecha/hora.

FIX: inferir la fecha desde API-Football matcheando por el equipo REAL (el local
sembrado: Recoleta, Olimpia, River, etc.) dentro de las fixtures de OCTAVOS de la
liga 11 (Sudamericana). Se toma la fecha de esa fixture y se setea partido.fecha
(y api_fixture_id si se puede).

Uso:
  python inferir_fechas_octavos_sudamericana.py            # DRY-RUN (no escribe)
  python inferir_fechas_octavos_sudamericana.py --apply    # aplica los cambios
"""
import sys, json, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timezone
import psycopg2

APPLY = "--apply" in sys.argv
API_KEY = "f13bee776659e2c20c715a81ecff2307"
BASE = "https://v3.football.api-sports.io"
TORNEO_ID = 14
LEAGUE_ID = 11   # Copa Sudamericana en API-Football

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()

# Alias para nombres que difieren entre la BD y API-Football.
ALIAS = {
    "boca juniors": ["boca juniors", "boca"],
    "recoleta": ["recoleta"],
    "bragantino": ["bragantino", "rb bragantino", "red bull bragantino"],
    "atletico mineiro": ["atletico mineiro", "atletico mg", "atletico-mg"],
    "cienciano": ["cienciano"],
    "botafogo": ["botafogo"],
    "vasco da gama": ["vasco da gama", "vasco"],
    "olimpia": ["olimpia"],
    "independiente santa fe": ["independiente santa fe", "santa fe"],
    "river plate": ["river plate", "river"],
    "tigre": ["tigre"],
    "montevideo city torque": ["montevideo city torque", "torque", "city torque"],
    "santos": ["santos"],
    "macara": ["macara"],
    "gremio": ["gremio"],
    "sao paulo": ["sao paulo"],
}
def variantes(nombre):
    n = norm(nombre)
    return ALIAS.get(n, [n])

def api_get(path):
    url = BASE + path
    req = urllib.request.Request(url, headers={"x-apisports-key": API_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

# Temporada del torneo (fallback 2026)
cur.execute("SELECT COALESCE(api_season, 2026) FROM torneo WHERE id=%s", (TORNEO_ID,))
row = cur.fetchone()
season = (row[0] if row and row[0] else 2026)
print(f"== Sudamericana torneo={TORNEO_ID} liga={LEAGUE_ID} season={season} ==\n")

# Octavos (ronda16) del torneo 14
cur.execute("""
    SELECT p.id, p.fecha, p.api_fixture_id,
           el.nombre AS local_nombre, el.api_team_id AS local_api,
           ev.nombre AS visit_nombre
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id=%s AND f.tipo='ronda16'
    ORDER BY p.id
""", (TORNEO_ID,))
octavos = cur.fetchall()
print(f"Octavos en BD: {len(octavos)}")
for o in octavos:
    print(f"  P{o[0]}  fecha={o[1]}  api_fix={o[2]}  {o[3]}  vs  {o[5]}")
print()

# Fixtures de la liga/temporada
try:
    data = api_get(f"/fixtures?league={LEAGUE_ID}&season={season}")
except Exception as e:
    print(f"[ERROR API] {e}"); sys.exit(1)
fixtures = data.get("response", [])
print(f"Fixtures traidos de API-Football: {len(fixtures)}")

# Rondas distintas (para ver como se llaman los octavos en la API)
rounds = {}
for fx in fixtures:
    rn = fx.get("league", {}).get("round", "")
    rounds[rn] = rounds.get(rn, 0) + 1
print("Rondas disponibles:")
for rn, c in sorted(rounds.items()):
    print(f"   [{c:2d}] {rn}")
print()

def es_octavos(rn):
    r = rn.lower()
    if "play" in r:            # "Knockout Round Play-offs" = 16avos, NO octavos
        return False
    return ("8th final" in r) or ("octavos" in r) or ("round of 16" in r)

oct_fix = [fx for fx in fixtures if es_octavos(fx.get("league", {}).get("round", ""))]
print(f"Fixtures de OCTAVOS detectadas: {len(oct_fix)}")
for fx in oct_fix:
    h = fx["teams"]["home"]["name"]; a = fx["teams"]["away"]["name"]
    print(f"   {fx['fixture']['date']}  {h}  vs  {a}   (fix={fx['fixture']['id']})")
print()

# Matching por la PIERNA exacta: home==local (y, si se puede, away==visit).
# Cada llave es ida y vuelta; el partido de la BD con local=X es la pierna donde
# X juega de LOCAL -> se busca la fixture de la API donde X es el equipo de casa.
def _hit(name, vs):
    n = norm(name)
    return any(norm(v) == n or norm(v) in n or n in norm(v) for v in vs)

cambios = []
usadas = set()   # no reusar la misma fixture para dos piernas
for o in octavos:
    pid, fecha_actual, api_fix, local_nombre, local_api, visit_nombre = o
    vs_local = variantes(local_nombre)
    vs_visit = variantes(visit_nombre)
    match = None
    # 1) preferido: home==local Y away==visit (identifica la pierna exacta)
    for fx in oct_fix:
        if fx["fixture"]["id"] in usadas:
            continue
        if _hit(fx["teams"]["home"]["name"], vs_local) and _hit(fx["teams"]["away"]["name"], vs_visit):
            match = fx; break
    # 2) fallback: home==local (la pierna donde el local juega de local)
    if not match:
        for fx in oct_fix:
            if fx["fixture"]["id"] in usadas:
                continue
            if _hit(fx["teams"]["home"]["name"], vs_local):
                match = fx; break
    # 3) fallback: away==visit (misma pierna; sirve si NUESTRO local difiere del
    #    nombre en la API, ej. la BD tiene 'Gremio' donde la API tiene 'Bolivar').
    if not match:
        for fx in oct_fix:
            if fx["fixture"]["id"] in usadas:
                continue
            if _hit(fx["teams"]["away"]["name"], vs_visit):
                match = fx; break
    if not match:
        print(f"[SIN MATCH] P{pid} {local_nombre} (local) vs {visit_nombre}: no encontre su pierna de octavos en la API")
        continue
    usadas.add(match["fixture"]["id"])
    iso = match["fixture"]["date"]           # ej '2026-08-19T23:30:00+00:00'
    dt = datetime.fromisoformat(iso).astimezone(timezone.utc).replace(tzinfo=None)
    fixid = match["fixture"]["id"]
    print(f"[MATCH] P{pid} {local_nombre} (local) vs {visit_nombre} -> {dt} UTC  "
          f"(fix={fixid}, API: {match['teams']['home']['name']} vs {match['teams']['away']['name']})")
    cambios.append((pid, dt, fixid))

print(f"\nTotal a actualizar: {len(cambios)}")
if not APPLY:
    print("\n(DRY-RUN) No se escribio nada. Corre con --apply para setear las fechas.")
    sys.exit(0)

for pid, dt, fixid in cambios:
    cur.execute("""UPDATE partido
                   SET fecha = %s,
                       api_fixture_id = COALESCE(api_fixture_id, %s)
                   WHERE id = %s""", (dt, fixid, pid))
conn.commit()
print(f"\nAPLICADO: {len(cambios)} partidos de octavos con fecha inferida.")
