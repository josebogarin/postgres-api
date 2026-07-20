# -*- coding: utf-8 -*-
"""list_cherem_globales.py — SOLO LECTURA. Lista globales A-G de uno o varios
apostadores (por defecto cherem y hs) con prediccion, resultado real y puntaje."""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

TID = 2
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")
USERS = [a.lower() for a in sys.argv[1:]] or ["cherem", "hs"]

def p(*a): print(*a); sys.stdout.flush()

becbuc = psycopg2.connect(dbname="becbuc", **DB)
appdb  = psycopg2.connect(dbname="app_db", **DB)
bc = becbuc.cursor(cursor_factory=RealDictCursor)
ac = appdb.cursor(cursor_factory=RealDictCursor)

# mapa equipo id -> nombre
bc.execute("SELECT id, nombre FROM equipo")
eq = {r["id"]: r["nombre"] for r in bc.fetchall()}
def en(i): return eq.get(i, f"id={i}") if i is not None else "—"

# resultados reales del torneo (compartidos)
bc.execute(f"""SELECT p.equipo_local_id, p.equipo_visitante_id, p.equipo_clasificado_id
               FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE p.torneo_id={TID} AND f.tipo='final' AND p.estado='finalizado' LIMIT 1""")
fin = bc.fetchone() or {}
bc.execute(f"SELECT resultado_goleador, resultado_peor_equipo_id FROM torneo WHERE id={TID}")
tor = bc.fetchone() or {}
campeon_real = en(fin.get("equipo_clasificado_id"))
finalistas_real = f"{en(fin.get('equipo_local_id'))} / {en(fin.get('equipo_visitante_id'))}"

def row(letra, concepto, pred, real, pts, maxp):
    p(f"  {letra}  {concepto:<20} | pred: {str(pred):<22} | real: {str(real):<20} | {str(pts)+'/'+str(maxp):>6}")

for uname in USERS:
    ac.execute("SELECT id, username, COALESCE(nombre,'') AS nombre FROM users WHERE LOWER(username)=%s", (uname,))
    u = ac.fetchone()
    if not u:
        p(f"\n(no se encontro '{uname}')"); continue
    uid = u["id"]
    bc.execute(f"SELECT * FROM apuesta_global WHERE torneo_id={TID} AND apostador_id={uid}")
    ag = bc.fetchone() or {}
    bc.execute(f"SELECT * FROM puntaje_global WHERE torneo_id={TID} AND apostador_id={uid}")
    pg = bc.fetchone() or {}

    p("\n" + "=" * 70)
    p(f" GLOBALES A-G — {u['username']} (id={uid})")
    p("=" * 70)
    row("A", "Campeon",        en(ag.get("pred_campeon_id")), campeon_real, pg.get("pts_campeon",0), 20)
    row("B", "Finalistas",     f"{en(ag.get('pred_finalista1_id'))} / {en(ag.get('pred_finalista2_id'))}", finalistas_real, pg.get("pts_finalistas",0), 20)
    row("C", "Goleador",       ag.get("pred_goleador"), tor.get("resultado_goleador"), pg.get("pts_goleador",0), 20)
    row("D", "Peor equipo",    en(ag.get("pred_peor_equipo_id")), en(tor.get("resultado_peor_equipo_id")), pg.get("pts_peor_equipo",0), 20)
    row("E", "Mayor goleada",  f"gan {ag.get('pred_goleada_ganador')} / perd {ag.get('pred_goleada_perdedor')}", "(max dif)", pg.get("pts_mayor_goleada",0), 20)
    row("F", "Etapa Paraguay", ag.get("pred_etapa_paraguay"), "ronda16 (Octavos)", pg.get("pts_etapa_paraguay",0), 6)
    row("G", "Goles Paraguay", ag.get("pred_goles_paraguay"), "(suma goles PY)", pg.get("pts_goles_paraguay",0), 6)
    p("  " + "-" * 66)
    p(f"  TOTAL GLOBALES BD: {pg.get('pts_total', 0)} / 112")

p("=" * 70)
bc.close(); ac.close(); becbuc.close(); appdb.close()
