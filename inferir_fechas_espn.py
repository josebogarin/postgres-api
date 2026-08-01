# -*- coding: utf-8 -*-
"""
inferir_fechas_espn.py

Setea fecha/hora de la fase KO desde ESPN (fuente precisa: hora exacta por partido,
en UTC). Sirve para Sudamericana y Libertadores (la API-Football no es confiable en
fecha/hora para estas fases: trae placeholders).

Uso:
  python inferir_fechas_espn.py <sudamericana|libertadores> [--apply]
Ej:
  python inferir_fechas_espn.py sudamericana          (DRY-RUN)
  python inferir_fechas_espn.py libertadores --apply
"""
import sys, json, unicodedata, urllib.request
from datetime import datetime, timezone, timedelta
import psycopg2

TORNEOS = {
    "sudamericana": {"torneo_id": 14, "league": "conmebol.sudamericana"},
    "libertadores": {"torneo_id": 1,  "league": "conmebol.libertadores"},
}
FASE_TIPO = "ronda16"                 # octavos
DATES     = "20260801-20260930"       # rango amplio; se filtra por partido programado

APPLY = "--apply" in sys.argv
key = next((a for a in sys.argv[1:] if not a.startswith("-")), "sudamericana").lower()
if key not in TORNEOS:
    print(f"Torneo desconocido: {key}. Use: sudamericana | libertadores"); sys.exit(1)
TORNEO_ID  = TORNEOS[key]["torneo_id"]
ESPN_LEAGUE = TORNEOS[key]["league"]

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return "".join(c for c in s.lower() if c.isalnum() or c == " ").strip()

# Alias BD -> variantes que puede usar ESPN (nombre en displayName).
ALIAS = {
    # Sudamericana
    "boca juniors": ["boca juniors", "boca"],
    "recoleta": ["deportivo recoleta", "recoleta"],
    "bragantino": ["red bull bragantino", "rb bragantino", "bragantino"],
    "atletico mineiro": ["atletico-mg", "atletico mg", "atletico mineiro"],
    "cienciano": ["cienciano del cusco", "cienciano"],
    "botafogo": ["botafogo"],
    "vasco da gama": ["vasco da gama", "vasco"],
    "olimpia": ["club olimpia", "olimpia"],
    "independiente santa fe": ["independiente santa fe", "santa fe"],
    "river plate": ["river plate", "river"],
    "tigre": ["tigre"],
    "montevideo city torque": ["montevideo city torque", "city torque", "torque"],
    "santos": ["santos"],
    "macara": ["macara"],
    "gremio": ["gremio", "bolivar"],   # override manual (en ESPN esa llave es Bolivar)
    "sao paulo": ["sao paulo"],
    # Libertadores (alias comunes; el matcheo tambien cae al nombre normalizado)
    "atletico nacional": ["atletico nacional", "nacional"],
    "flamengo": ["flamengo"],
    "palmeiras": ["palmeiras"],
    "river": ["river plate", "river"],
    "libertad": ["libertad"],
    "cerro porteno": ["cerro porteno"],
    "estudiantes lp": ["estudiantes de la plata", "estudiantes la plata", "estudiantes lp"],
    "u catolica": ["universidad catolica", "u catolica"],
    "sao paulo fc": ["sao paulo"],
    "velez": ["velez sarsfield", "velez"],
    "racing": ["racing club", "racing"],
    "penarol": ["penarol"],
    "internacional": ["internacional", "inter"],
    "botafogo fr": ["botafogo"],
}
def variantes(nombre):
    return ALIAS.get(norm(nombre), [norm(nombre)])
def hit(name, vs):
    n = norm(name)
    return any(norm(v) == n or norm(v) in n or n in norm(v) for v in vs)

def espn_events():
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{ESPN_LEAGUE}/scoreboard?dates={DATES}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    out = []
    for e in data.get("events", []):
        state = (((e.get("status") or {}).get("type")) or {}).get("state", "")
        if state == "post":     # ya jugado -> evita colision con fase de grupos
            continue
        dt = e.get("date")
        comp = (e.get("competitions") or [{}])[0]
        home = away = None
        for c in comp.get("competitors", []):
            t = (c.get("team") or {})
            nm = t.get("displayName") or t.get("name") or t.get("shortDisplayName")
            if c.get("homeAway") == "home": home = nm
            elif c.get("homeAway") == "away": away = nm
        if dt and home and away:
            out.append((dt, home, away, state))
    return out

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()
cur.execute("""
    SELECT p.id, p.fecha,
           COALESCE(el.nombre_es, el.nombre), COALESCE(ev.nombre_es, ev.nombre)
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id=%s AND f.tipo=%s
    ORDER BY p.id
""", (TORNEO_ID, FASE_TIPO))
partidos = cur.fetchall()
print(f"== {key.upper()} (torneo {TORNEO_ID}) · {FASE_TIPO} · fuente ESPN {ESPN_LEAGUE} ==")
print(f"Partidos en BD: {len(partidos)}")

try:
    evs = espn_events()
except Exception as e:
    print(f"[ERROR ESPN] {e}"); sys.exit(1)
print(f"Eventos ESPN programados en {DATES}: {len(evs)}")
for dt, h, a, st in evs:
    py = (datetime.fromisoformat(dt.replace('Z','+00:00')).astimezone(timezone.utc) - timedelta(hours=3))
    print(f"   {dt}  ({py.strftime('%d/%m %H:%M')} PY) [{st}]  {a}  at  {h}")
print()

cambios = []
usadas = set()
for pid, fecha_actual, local, visit in partidos:
    vs_l = variantes(local); vs_v = variantes(visit)
    match = None
    for i, (dt, h, a, st) in enumerate(evs):
        if i in usadas: continue
        if hit(h, vs_l) and hit(a, vs_v):
            match = (i, dt); break
    if not match:
        for i, (dt, h, a, st) in enumerate(evs):
            if i in usadas: continue
            if hit(h, vs_l):
                match = (i, dt); break
    if not match:
        for i, (dt, h, a, st) in enumerate(evs):
            if i in usadas: continue
            if hit(a, vs_v) and not hit(h, vs_v):
                match = (i, dt); break
    if not match:
        print(f"[SIN MATCH] P{pid} {local} (local) vs {visit}")
        continue
    idx, dt = match
    usadas.add(idx)
    d_utc = datetime.fromisoformat(dt.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    py = d_utc - timedelta(hours=3)
    print(f"[MATCH] P{pid} {local} vs {visit} -> {d_utc} UTC  ({py.strftime('%d/%m %H:%M')} PY)  antes: {fecha_actual}")
    cambios.append((pid, d_utc))

print(f"\nTotal a actualizar: {len(cambios)} / {len(partidos)}")
if not APPLY:
    print("(DRY-RUN) No se escribio nada. Agrega --apply para aplicar.")
    sys.exit(0)
for pid, d_utc in cambios:
    cur.execute("UPDATE partido SET fecha=%s WHERE id=%s", (d_utc, pid))
conn.commit()
print(f"APLICADO: {len(cambios)} partidos actualizados desde ESPN.")
