# -*- coding: utf-8 -*-
"""
Limpia el KO de la Copa Sudamericana 2026 (torneo_id=14) para recargar el fixture
del usuario sin la mezcla de datos viejos de API-Football:
  - Pone TODOS los partidos de ronda32 (16avos) en "Por Definir" (fecha/sede NULL).
  - NO toca la ronda16 (octavos): ya esta bien poblada.
Despues volver a correr SOLO el 16avos loader (los octavos ya estan).
Ejecutar:  python reset_sudamericana_ko.py [--apply]
"""
import sys
import psycopg2

APPLY = "--apply" in sys.argv
TORNEO_ID = 14

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

# equipo Por Definir
cur.execute("SELECT id FROM equipo WHERE lower(nombre) IN ('por definir','tbd') OR lower(nombre_es) IN ('por definir','tbd') ORDER BY id LIMIT 1")
r = cur.fetchone()
if not r:
    print("No existe equipo 'Por Definir'."); sys.exit(1)
tbd = r[0]
print(f"Por Definir id={tbd}")

# ronda32
cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32'", (TORNEO_ID,))
f32 = cur.fetchone()
cur.execute("SELECT count(*) FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s AND f.tipo='ronda32'", (TORNEO_ID,))
n32 = cur.fetchone()[0]
cur.execute("SELECT count(*) FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s AND f.tipo='ronda16'", (TORNEO_ID,))
n16 = cur.fetchone()[0]
print(f"ronda32 partidos={n32}  |  ronda16 partidos={n16}")

if APPLY:
    cur.execute("""UPDATE partido SET equipo_local_id=%s, equipo_visitante_id=%s,
                   fecha=NULL, sede=NULL, ciudad=NULL, estado='programado'
                   WHERE fase_id IN (SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda32')""",
                (tbd, tbd, TORNEO_ID))
    print(f"ronda32 -> {cur.rowcount} partidos reseteados a Por Definir")
    print("ronda16 (octavos) -> NO se toca (ya esta correcta)")
    conn.commit(); print("== COMMIT ok ==")
else:
    print("== DRY-RUN (agrega --apply para limpiar) ==")
cur.close(); conn.close()
