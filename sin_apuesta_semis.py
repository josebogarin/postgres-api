# -*- coding: utf-8 -*-
"""
sin_apuesta_semis.py
Lista los apostadores que NO cargaron apuesta en la fase SEMIFINAL (P101-P102)
en la BD. Compara contra el padron de participantes del torneo (todos los que
tienen al menos una apuesta en el torneo 2). Solo lectura.

Uso:
  backend\\.venv\\Scripts\\python.exe sin_apuesta_semis.py
"""
import sys, os
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
CONN_APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
TORNEO_ID = 2
NF_MIN, NF_MAX = 101, 102

conn_bec = psycopg2.connect(CONN_BEC); conn_app = psycopg2.connect(CONN_APP)
cur_bec = conn_bec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur_app = conn_app.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Padron: participantes del torneo (con al menos una apuesta en torneo 2)
cur_bec.execute("""
    SELECT DISTINCT a.apostador_id FROM apuesta a
    JOIN partido p ON p.id=a.partido_id
    JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=%s
""", (TORNEO_ID,))
padron = {r['apostador_id'] for r in cur_bec.fetchall()}

# Partidos semifinal
cur_bec.execute("""
    SELECT p.id, p.numero_fifa FROM partido p JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN %s AND %s
""", (TORNEO_ID, NF_MIN, NF_MAX))
partidos = {f"P{r['numero_fifa']:03d}": r['id'] for r in cur_bec.fetchall()}

# Quien aposto cada partido de semifinal
apostaron = {}  # pid_key -> set(apostador_id)
for key, pid in partidos.items():
    cur_bec.execute("SELECT apostador_id FROM apuesta WHERE partido_id=%s", (pid,))
    apostaron[key] = {r['apostador_id'] for r in cur_bec.fetchall()}

# Usernames
cur_app.execute("SELECT id, username, nombre FROM users")
uname = {r['id']: (r['username'] or str(r['id'])) for r in cur_app.fetchall()}

print("="*60)
print("APOSTADORES SIN APUESTA EN SEMIFINAL (P101-P102)")
print("="*60)
print(f"Padron de participantes (torneo {TORNEO_ID}): {len(padron)}")
for key in sorted(partidos):
    faltan = sorted(padron - apostaron.get(key, set()))
    print(f"\n{key}: {len(apostaron.get(key,set()))} apostaron, {len(faltan)} sin apuesta")
    if faltan:
        for uid in faltan:
            print(f"   - {uname.get(uid, uid)} (id={uid})")

# Sin apuesta en NINGUN partido de semifinal
sin_ninguna = sorted(padron - set().union(*apostaron.values()) if apostaron else padron)
print("\n" + "-"*60)
if not sin_ninguna:
    print("Todos los participantes cargaron al menos una apuesta en semifinal.")
else:
    print(f"NO cargaron NINGUNA apuesta de semifinal ({len(sin_ninguna)}):")
    for uid in sin_ninguna:
        print(f"   - {uname.get(uid, uid)} (id={uid})")

conn_bec.close(); conn_app.close()
