# -*- coding: utf-8 -*-
"""
Carga el fixture oficial de 16avos (ronda32) de la Copa Sudamericana 2026
(torneo_id=14). Como los partidos estan TODOS en "Por Definir", CREA los equipos
(si no existen) y los ASIGNA a los 16 partidos TBD: ida (X local) + vuelta (Y local),
con fechas UTC y sedes. Idempotente (re-corre matcheando por par de equipos).
Ejecutar:  python cargar_fixture_sudamericana_16avos.py [--apply]
"""
import sys, datetime
import psycopg2

APPLY = "--apply" in sys.argv
TORNEO_ID = 14
U = datetime.datetime

# (X = local IDA, Y = local VUELTA, ida_utc, vue_utc, ida_sede, ida_ciudad, vue_sede, vue_ciudad)
TIES = [
    ("Nacional", "Tigre", U(2026,7,21,22,0), U(2026,7,28,22,0),
     "Gran Parque Central", "Montevideo", "Jose Dellagiovanna", "Victoria"),
    ("Universidad Central", "Santos", U(2026,7,22,1,30), U(2026,7,29,0,30),
     "Olimpico UCV", "Caracas", "Urbano Caldeira", "Santos"),
    ("Independiente Medellin", "Vasco da Gama", U(2026,7,23,0,0), U(2026,7,29,22,0),
     "Atanasio Girardot", "Medellin", "Sao Januario", "Rio de Janeiro"),
    ("Lanus", "Cienciano", U(2026,7,23,0,30), U(2026,7,30,2,30),
     "Ciudad de Lanus", "Lanus", "Inca Garcilaso de la Vega", "Cusco"),
    ("Sporting Cristal", "Bragantino", U(2026,7,23,0,30), U(2026,7,30,0,30),
     "Nacional del Peru", "Lima", "A definir", "A definir"),
    ("Bolivar", "Gremio", U(2026,7,23,23,0), U(2026,7,30,22,0),
     "Hernando Siles", "La Paz", "Arena do Gremio", "Porto Alegre"),
    ("Independiente Santa Fe", "Caracas", U(2026,7,24,2,30), U(2026,7,31,1,30),
     "Nemesio Camacho El Campin", "Bogota", "Olimpico UCV", "Caracas"),
    ("Boca Juniors", "O'Higgins", U(2026,7,24,0,30), U(2026,7,31,1,30),
     "La Bombonera", "Buenos Aires", "El Teniente", "Rancagua"),
]

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32'", (TORNEO_ID,))
r = cur.fetchone()
if not r:
    print("No existe fase ronda32 (16avos) para torneo", TORNEO_ID); sys.exit(1)
fase_id = r[0]

def get_or_create_eq(nombre, tipo="club"):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s OR nombre_es=%s LIMIT 1", (nombre, nombre))
    x = cur.fetchone()
    if x:
        return x[0], False
    if not APPLY:
        return None, True
    cur.execute("INSERT INTO equipo (nombre, nombre_es, tipo) VALUES (%s,%s,%s) RETURNING id",
                (nombre, nombre, tipo))
    return cur.fetchone()[0], True

TBD = ("tbd", "por definir")
def es_tbd(n): return n is None or str(n).strip().lower() in TBD

cur.execute("""SELECT p.id, p.equipo_local_id, p.equipo_visitante_id, el.nombre, ev.nombre
               FROM partido p LEFT JOIN equipo el ON el.id=p.equipo_local_id
               LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s ORDER BY p.id""", (fase_id,))
partidos=[{"id":a,"lid":b,"vid":c,"ln":d,"vn":e} for (a,b,c,d,e) in cur.fetchall()]
pool=[p["id"] for p in partidos if es_tbd(p["ln"]) or es_tbd(p["vn"]) or p["lid"] is None or p["vid"] is None]
print(f"Fase 16avos id={fase_id}: {len(partidos)} partidos, {len(pool)} en Por Definir")

def real_ids(p):
    if es_tbd(p["ln"]) or es_tbd(p["vn"]) or p["lid"] is None or p["vid"] is None: return None
    return frozenset((p["lid"], p["vid"]))

def upd(pid, local, visit, fecha, sede, ciudad):
    print(f"      UPDATE partido {pid}: local_id={local} visit_id={visit} fecha={fecha} sede={sede}")
    if APPLY:
        cur.execute("""UPDATE partido SET equipo_local_id=%s, equipo_visitante_id=%s, fecha=%s,
                       sede=%s, ciudad=%s, estado='programado' WHERE id=%s""",
                    (local, visit, fecha, sede, ciudad, pid))

for X, Y, ida_utc, vue_utc, isede, icd, vsede, vcd in TIES:
    xid, xnew = get_or_create_eq(X)
    yid, ynew = get_or_create_eq(Y)
    print(f"\n{X}(id={xid}{' NUEVO' if xnew else ''}) vs {Y}(id={yid}{' NUEVO' if ynew else ''})")
    key = frozenset((xid, yid)) if (xid and yid) else None
    existing = [p for p in partidos if key and real_ids(p) == key]
    if len(existing) >= 2:
        legs = sorted(existing, key=lambda p: p["id"])
        ida_id, vue_id = legs[0]["id"], legs[1]["id"]
    else:
        if len(pool) < 2:
            print("   !! sin partidos TBD suficientes"); continue
        ida_id = pool.pop(0); vue_id = pool.pop(0)
    upd(ida_id, xid, yid, ida_utc, isede, icd)   # IDA: X local
    upd(vue_id, yid, xid, vue_utc, vsede, vcd)   # VUELTA: Y local

if APPLY:
    conn.commit(); print("\n== COMMIT ok ==")
else:
    print("\n== DRY-RUN (agrega --apply para escribir) ==")
cur.close(); conn.close()
