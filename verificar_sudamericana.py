# -*- coding: utf-8 -*-
"""verificar_sudamericana.py - Chequeo integral del bracket de Sudamericana (torneo 14)."""
import psycopg2
TID=14
conn=psycopg2.connect(host="localhost",port=5432,dbname="becbuc",user="app_user",password="superpassword")
cur=conn.cursor()
def fase(t):
    cur.execute("SELECT id,nombre FROM fase WHERE torneo_id=%s AND tipo=%s",(TID,t)); return cur.fetchone()

print("======== VERIFICACION SUDAMERICANA (torneo 14) ========\n")
# OCTAVOS
of=fase('ronda16')
cur.execute("""SELECT p.id,el.nombre,ev.nombre,p.fecha FROM partido p
               JOIN equipo el ON el.id=p.equipo_local_id JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s ORDER BY p.id""",(of[0],))
octs=cur.fetchall()
placeholders=[r for r in octs if 'gan.' in (r[1] or '').lower() or 'gan.' in (r[2] or '').lower()]
print(f"-- OCTAVOS ({len(octs)} partidos) --")
for pid,ln,vn,fe in octs: print(f"  p{pid}: {ln} vs {vn}")
print(f"\n  Placeholders 'Gan.' sin resolver: {len(placeholders)} {'OK' if not placeholders else '<-- FALTAN RESOLVER'}")

# R32 penales de las 2 llaves que fueron a tanda
print("\n-- R32: definiciones por penales --")
rf=fase('ronda32')
for frag in ("nacional","bolivar"):
    cur.execute("""SELECT p.id,el.nombre,ev.nombre,p.goles_local,p.goles_visitante,
                          p.penales_local,p.penales_visitante,p.fecha
                   FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                                  JOIN equipo ev ON ev.id=p.equipo_visitante_id
                   WHERE p.fase_id=%s AND (LOWER(el.nombre) LIKE %s OR LOWER(ev.nombre) LIKE %s)
                   ORDER BY p.fecha""",(rf[0],f"%{frag}%",f"%{frag}%"))
    for r in cur.fetchall():
        pid,ln,vn,gl,gv,pl,pv,fe=r
        pen = f"pen {pl}-{pv}" if pl is not None else "SIN PENALES"
        print(f"  p{pid}: {ln} {gl}-{gv} {vn}   [{pen}]")

# Conteo total de partidos por fase
print("\n-- Conteo por fase --")
cur.execute("""SELECT f.tipo,COUNT(*) FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE p.torneo_id=%s GROUP BY f.tipo,f.orden ORDER BY f.orden""",(TID,))
for t,c in cur.fetchall(): print(f"  {t}: {c}")

print("\n======== FIN ========")
cur.close(); conn.close()
