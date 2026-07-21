# -*- coding: utf-8 -*-
"""
Octavos (ronda16) de la Copa Sudamericana 2026 (torneo_id=14): cada sembrado con
su rival ya definido = ganador de una llave puntual de 16avos.
Crea la fase + partidos si no existen; si ya existen, ACTUALIZA el rival (reemplaza
el "Por Definir" generico por el placeholder "Gan. X/Y" correcto).
Ejecutar:  python poblar_octavos_sudamericana.py [--apply]
"""
import sys
import psycopg2

APPLY = "--apply" in sys.argv
TORNEO_ID = 14

# (sembrado, sede_vuelta, ciudad_vuelta, rival = ganador de 16avos)
SEEDS = [
    ("Recoleta",               "Rio Parapiti",        "Asuncion",       "Gan. Boca/O'Higgins"),
    ("Atletico Mineiro",       "Arena MRV",           "Belo Horizonte", "Gan. S.Cristal/Bragantino"),
    ("Botafogo",               "Nilton Santos",       "Rio de Janeiro", "Gan. Lanus/Cienciano"),
    ("Olimpia",                "Defensores del Chaco","Asuncion",       "Gan. I.Medellin/Vasco"),
    ("River Plate",            "Monumental",          "Buenos Aires",   "Gan. Santa Fe/Caracas"),
    ("Montevideo City Torque", "Centenario",          "Montevideo",     "Gan. Nacional/Tigre"),
    ("Macara",                 "Bellavista",          "Ambato",         "Gan. U.Central/Santos"),
    ("Sao Paulo",              "Morumbi",             "Sao Paulo",      "Gan. Bolivar/Gremio"),
]

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'", (TORNEO_ID,))
r = cur.fetchone()
fase_id = r[0] if r else None

def get_or_create_eq(nombre, tipo="club"):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s OR nombre_es=%s LIMIT 1", (nombre, nombre))
    x = cur.fetchone()
    if x: return x[0], False
    if not APPLY: return None, True
    cur.execute("INSERT INTO equipo (nombre, nombre_es, tipo) VALUES (%s,%s,%s) RETURNING id",
                (nombre, nombre, tipo))
    return cur.fetchone()[0], True

if fase_id is None:
    print("Fase octavos NO existe -> se creara (Octavos de Final, ronda16, orden 20).")
    if APPLY:
        cur.execute("""INSERT INTO fase (torneo_id, nombre, tipo, orden)
                       VALUES (%s,'Octavos de Final','ronda16',20) RETURNING id""", (TORNEO_ID,))
        fase_id = cur.fetchone()[0]; print(f"Fase creada id={fase_id}")
else:
    print(f"Fase octavos id={fase_id} (se actualizan/crean los cruces).")

def mk_partido(local, visit, sede, ciudad):
    print(f"      INSERT partido: local={local} visit={visit} sede={sede}")
    if APPLY:
        cur.execute("""INSERT INTO partido (fase_id, torneo_id, equipo_local_id, equipo_visitante_id,
                       estado, sede, ciudad) VALUES (%s,%s,%s,%s,'programado',%s,%s)""",
                    (fase_id, TORNEO_ID, local, visit, sede, ciudad))

for nombre, vsede, vcd, rival in SEEDS:
    sid, snew = get_or_create_eq(nombre)
    rid, rnew = get_or_create_eq(rival)
    print(f"\n{nombre}(id={sid}) vs {rival}(id={rid}){'  [equipos nuevos]' if (snew or rnew) else ''}")
    # partidos existentes del sembrado en octavos
    parts = []
    if fase_id and sid:
        cur.execute("""SELECT id, equipo_local_id, equipo_visitante_id FROM partido
                       WHERE fase_id=%s AND (equipo_local_id=%s OR equipo_visitante_id=%s)
                       ORDER BY id""", (fase_id, sid, sid))
        parts = cur.fetchall()
    if len(parts) >= 2:
        for pid, lid, vid in parts:
            if lid == sid:   # VUELTA: sembrado local, rival visitante
                print(f"      UPDATE {pid}: visit -> {rid} (vuelta {nombre} local)")
                if APPLY:
                    cur.execute("UPDATE partido SET equipo_visitante_id=%s, sede=%s, ciudad=%s WHERE id=%s",
                                (rid, vsede, vcd, pid))
            else:            # IDA: rival local, sembrado visitante
                print(f"      UPDATE {pid}: local -> {rid} (ida rival local)")
                if APPLY:
                    cur.execute("UPDATE partido SET equipo_local_id=%s, sede='A definir', ciudad='A definir' WHERE id=%s",
                                (rid, pid))
    else:
        mk_partido(rid, sid, "A definir", "A definir")   # ida
        mk_partido(sid, rid, vsede, vcd)                 # vuelta

if APPLY:
    conn.commit(); print("\n== COMMIT ok ==")
else:
    print("\n== DRY-RUN (agrega --apply para escribir) ==")
cur.close(); conn.close()
