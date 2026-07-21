# -*- coding: utf-8 -*-
"""
Busca en API-Football el logo (y api_team_id) de los equipos que se crearon a mano
para los fixtures de Sudamericana, DESAMBIGUANDO POR PAIS (hay varios "Nacional",
"Recoleta", etc.). Actualiza equipo.logo_url solo de los que estan sin logo.
Ejecutar:  python buscar_logos_equipos.py [--apply] [--force]
  --force  : tambien re-busca los que ya tienen logo.
"""
import sys, json, time, urllib.parse, urllib.request
import psycopg2

APPLY = "--apply" in sys.argv
FORCE = "--force" in sys.argv
API_KEY = "f13bee776659e2c20c715a81ecff2307"
BASE = "https://v3.football.api-sports.io"

# (nombre en la BD, termino de busqueda, pais en API-Football)
MAP = [
    ("Nacional",                "Nacional",             "Paraguay"),
    ("Tigre",                   "Tigre",                "Argentina"),
    ("Universidad Central",     "Universidad Central",  "Venezuela"),
    ("Santos",                  "Santos",               "Brazil"),
    ("Independiente Medellin",  "Independiente Medellin","Colombia"),
    ("Vasco da Gama",           "Vasco DA Gama",        "Brazil"),
    ("Lanus",                   "Lanus",                "Argentina"),
    ("Cienciano",               "Cienciano",            "Peru"),
    ("Sporting Cristal",        "Sporting Cristal",     "Peru"),
    ("Bragantino",              "Bragantino",           "Brazil"),
    ("Bolivar",                 "Bolivar",              "Bolivia"),
    ("Gremio",                  "Gremio",               "Brazil"),
    ("Independiente Santa Fe",  "Independiente Santa Fe","Colombia"),
    ("Caracas",                 "Caracas",              "Venezuela"),
    ("Boca Juniors",            "Boca Juniors",         "Argentina"),
    ("O'Higgins",               "OHiggins",             "Chile"),
    ("Recoleta",                "Recoleta",             "Paraguay"),
    ("Atletico Mineiro",        "Atletico-MG",          "Brazil"),
    ("Botafogo",                "Botafogo",             "Brazil"),
    ("Olimpia",                 "Olimpia",              "Paraguay"),
    ("River Plate",             "River Plate",          "Argentina"),
    ("Montevideo City Torque",  "Torque",               "Uruguay"),
    ("Macara",                  "Macara",               "Ecuador"),
    ("Sao Paulo",               "Sao Paulo",            "Brazil"),
]

def api_teams(search):
    url = BASE + "/teams?search=" + urllib.parse.quote(search)
    req = urllib.request.Request(url, headers={"x-apisports-key": API_KEY})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()).get("response", [])

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

for db_name, search, pais in MAP:
    cur.execute("SELECT id, logo_url FROM equipo WHERE nombre=%s OR nombre_es=%s LIMIT 1", (db_name, db_name))
    row = cur.fetchone()
    if not row:
        print(f"[skip] {db_name}: no esta en la BD"); continue
    eid, logo_actual = row
    if logo_actual and not FORCE:
        print(f"[ok ya] {db_name}: ya tiene logo"); continue
    try:
        res = api_teams(search)
    except Exception as e:
        print(f"[ERR API] {db_name}: {e}"); continue
    # filtrar por pais
    cands = [x for x in res if (x.get("team",{}).get("country") or "").lower() == pais.lower()]
    pick = cands[0] if cands else (res[0] if res else None)
    if not pick:
        print(f"[NO MATCH] {db_name} (buscando '{search}' en {pais})"); continue
    t = pick["team"]
    aviso = "" if cands else "  <-- SIN match de pais, tomo el 1ro (REVISAR)"
    print(f"[{'match' if cands else '??? '}] {db_name} -> {t['name']} ({t.get('country')}) id={t['id']}{aviso}")
    print(f"           logo: {t.get('logo')}")
    if APPLY:
        # Solo logo_url (no tocar api_team_id: puede chocar con un equipo duplicado ya existente).
        cur.execute("UPDATE equipo SET logo_url=%s WHERE id=%s", (t.get("logo"), eid))
        conn.commit()  # commit por equipo: un error no aborta el resto
    time.sleep(0.3)

if APPLY:
    conn.commit(); print("\n== COMMIT ok ==")
else:
    print("\n== DRY-RUN (agrega --apply para guardar los logos) ==")
cur.close(); conn.close()
