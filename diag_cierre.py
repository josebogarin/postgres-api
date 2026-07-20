# -*- coding: utf-8 -*-
"""diag_cierre.py -- SOLO LECTURA. Estado actual + nombres de columnas de partido."""
import sys, os
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

TID = 2
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
conn = psycopg2.connect(CONN); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("="*64); print("DIAGNOSTICO CIERRE - SOLO LECTURA"); print("="*64)

print("\n== columnas de 'partido' (las que tienen 'minuto' o 'gol') ==")
cur.execute("""SELECT column_name FROM information_schema.columns
               WHERE table_name='partido' ORDER BY ordinal_position""")
cols = [r['column_name'] for r in cur.fetchall()]
print("   con minuto/gol:", [c for c in cols if 'minuto' in c.lower() or 'gol' in c.lower()])

print("\n== P103 / P104 (fila completa, campos clave) ==")
cur.execute("""SELECT p.*, el.nombre AS local, ev.nombre AS visit, ec.nombre AS clasificado
  FROM partido p JOIN fase f ON f.id=p.fase_id
  LEFT JOIN equipo el ON el.id=p.equipo_local_id
  LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
  LEFT JOIN equipo ec ON ec.id=p.equipo_clasificado_id
  WHERE f.torneo_id=%s AND p.numero_fifa IN (103,104) ORDER BY p.numero_fifa""", (TID,))
for r in cur.fetchall():
    print(f"\n   P{r['numero_fifa']} {r['local']} {r['goles_local']}-{r['goles_visitante']} {r['visit']}  clasifica={r['clasificado']}")
    print(f"      amarillas={r.get('amarillas')} rojas={r.get('rojas')} VAR={r.get('decisiones_var')} pen_partido={r.get('penales_partido')}")
    for c in cols:
        if 'minuto' in c.lower() or (('gol' in c.lower()) and 'goles' not in c.lower()):
            print(f"      {c} = {r.get(c)}")

print("\n== torneo: goleador / peor equipo / cerrado ==")
cur.execute("SELECT * FROM torneo WHERE id=%s", (TID,))
t = cur.fetchone()
for k in ('resultado_goleador','resultado_peor_equipo_id','cerrado','cerrado_at'):
    if k in t: print(f"   {k} = {t.get(k)}")

print("\n== pred_goleador spellings con 'mbap' ==")
cur.execute("""SELECT TRIM(pred_goleador) AS g, COUNT(*) AS n FROM apuesta_global
               WHERE torneo_id=%s AND pred_goleador ILIKE '%%mbap%%'
               GROUP BY TRIM(pred_goleador) ORDER BY n DESC""", (TID,))
for r in cur.fetchall(): print(f"   '{r['g']}' -> {r['n']}")

conn.close(); print("\n=== FIN DIAG ===")
