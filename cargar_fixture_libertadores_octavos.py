# -*- coding: utf-8 -*-
"""
Carga el fixture oficial de OCTAVOS de la Copa Libertadores 2026 (torneo_id=1)
en la BD becbuc: equipos ida (invirtiendo la vuelta), fechas en UTC y sedes.
Horas locales de cada sede convertidas a UTC. El front muestra hora Paraguay.
Ejecutar (uvicorn NO es necesario):  python cargar_fixture_libertadores_octavos.py [--apply]
Sin --apply hace dry-run (no escribe).
"""
import sys, datetime
import psycopg2

APPLY = "--apply" in sys.argv
TORNEO_ID = 1
U = datetime.datetime  # UTC naive

# (X = local de la IDA, Y = local de la VUELTA, ida_utc, vuelta_utc,
#  ida_sede, ida_ciudad, vuelta_sede, vuelta_ciudad)
TIES = [
    ("Fluminense", "Independ. Rivadavia", U(2026,8,11,22,0), U(2026,8,18,22,0),
     "Maracana", "Rio de Janeiro", "Malvinas Argentinas", "Mendoza"),
    ("Estudiantes L.P.", "U. Catolica", U(2026,8,12,0,30), U(2026,8,19,0,30),
     "UNO Jorge Luis Hirschi", "La Plata", "Claro Arena", "Santiago"),
    ("Deportes Tolima", "Independiente del Valle", U(2026,8,12,0,30), U(2026,8,19,0,30),
     "Manuel Murillo Toro", "Ibague", "Banco Guayaquil", "Quito"),
    ("Platense", "Coquimbo Unido", U(2026,8,12,22,0), U(2026,8,19,22,0),
     "Ciudad de Vicente Lopez", "Vicente Lopez", "Francisco Sanchez Rumoroso", "Coquimbo"),
    ("Palmeiras", "Cerro Porteno", U(2026,8,12,22,0), U(2026,8,19,23,0),
     "Allianz Parque", "Sao Paulo", "Ueno La Nueva Olla", "Asuncion"),
    ("Cruzeiro", "Flamengo", U(2026,8,13,0,30), U(2026,8,20,0,30),
     "Mineirao", "Belo Horizonte", "Maracana", "Rio de Janeiro"),
    ("Mirassol", "LDU de Quito", U(2026,8,13,22,0), U(2026,8,20,22,0),
     "Jose Maria de Campos Maia", "Mirassol", "Rodrigo Paz Delgado", "Quito"),
    ("Rosario Central", "Corinthians", U(2026,8,14,0,30), U(2026,8,21,0,30),
     "Gigante de Arroyito", "Rosario", "Neo Quimica Arena", "Sao Paulo"),
]

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'", (TORNEO_ID,))
row = cur.fetchone()
if not row:
    print("No existe fase ronda16 para torneo", TORNEO_ID); sys.exit(1)
fase_id = row[0]

def eqid(nombre):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s OR nombre_es=%s LIMIT 1", (nombre, nombre))
    r = cur.fetchone()
    if not r:
        print("!! equipo NO encontrado:", nombre); sys.exit(1)
    return r[0]

TBD = ("tbd", "por definir")
def es_tbd(nombre):
    return nombre is None or str(nombre).strip().lower() in TBD

cur.execute("""
    SELECT p.id, p.equipo_local_id, p.equipo_visitante_id, el.nombre, ev.nombre
    FROM partido p
    LEFT JOIN equipo el ON el.id=p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
    WHERE p.fase_id=%s ORDER BY p.id
""", (fase_id,))
partidos = [{"id": r[0], "lid": r[1], "vid": r[2], "ln": r[3], "vn": r[4]} for r in cur.fetchall()]
pool_tbd = [p["id"] for p in partidos if es_tbd(p["ln"]) or es_tbd(p["vn"]) or p["lid"] is None or p["vid"] is None]

def real_ids(p):
    if es_tbd(p["ln"]) or es_tbd(p["vn"]) or p["lid"] is None or p["vid"] is None:
        return None
    return frozenset((p["lid"], p["vid"]))

def upd(pid, local, visit, fecha, sede, ciudad):
    print(f"   UPDATE partido {pid}: local={local} visit={visit} fecha={fecha} sede={sede}")
    if APPLY:
        cur.execute("""UPDATE partido SET equipo_local_id=%s, equipo_visitante_id=%s,
                       fecha=%s, sede=%s, ciudad=%s, estado='programado'
                       WHERE id=%s""", (local, visit, fecha, sede, ciudad, pid))

for X, Y, ida_utc, vue_utc, isede, icd, vsede, vcd in TIES:
    xid, yid = eqid(X), eqid(Y)
    key = frozenset((xid, yid))
    matched = [p for p in partidos if real_ids(p) == key]
    print(f"\n{X} vs {Y}  (match existentes={len(matched)})")
    if len(matched) >= 2:
        legs = sorted(matched, key=lambda p: p["id"])
        ida_p, vue_p = legs[0]["id"], legs[1]["id"]
    elif len(matched) == 1:
        vue_p = matched[0]["id"]
        if not pool_tbd:
            print("   !! sin partido TBD libre para la ida"); continue
        ida_p = pool_tbd.pop(0)
    else:
        print("   !! no se encontro la vuelta (equipos reales)"); continue
    upd(ida_p, xid, yid, ida_utc, isede, icd)      # IDA: X local
    upd(vue_p, yid, xid, vue_utc, vsede, vcd)      # VUELTA: Y local

if APPLY:
    conn.commit(); print("\n== COMMIT ok ==")
else:
    print("\n== DRY-RUN (agrega --apply para escribir) ==")
cur.close(); conn.close()
