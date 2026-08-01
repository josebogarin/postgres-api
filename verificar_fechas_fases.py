# -*- coding: utf-8 -*-
"""
verificar_fechas_fases.py

CONTROL: por la precedencia de partidos en el Live, TODA fase deberia tener la
fecha/hora definida en todos sus partidos. Este script recorre los torneos
habilitados para el Live (mostrar_live=TRUE) — o el torneo que se pase como
argumento — y reporta por fase cuantos partidos estan SIN fecha, marcando las
fases incompletas.

Uso:
  python verificar_fechas_fases.py            # todos los torneos del Live
  python verificar_fechas_fases.py 14         # solo el torneo 14 (Sudamericana)
"""
import sys
import psycopg2

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

if len(sys.argv) > 1 and sys.argv[1].isdigit():
    torneos = [int(sys.argv[1])]
else:
    try:
        cur.execute("SELECT id FROM torneo WHERE COALESCE(mostrar_live, TRUE)=TRUE ORDER BY id")
        torneos = [r[0] for r in cur.fetchall()]
    except Exception:
        cur.execute("SELECT id FROM torneo ORDER BY id")
        torneos = [r[0] for r in cur.fetchall()]

total_incompletas = 0
for tid in torneos:
    cur.execute("SELECT COALESCE(nombre, CONCAT('torneo ', id)) FROM torneo WHERE id=%s", (tid,))
    row = cur.fetchone()
    tnombre = row[0] if row else f"torneo {tid}"
    cur.execute("""
        SELECT f.nombre, f.tipo, f.orden, COALESCE(f.bloqueada, FALSE),
               COUNT(p.id)                                   AS total,
               COUNT(*) FILTER (WHERE p.fecha IS NULL)       AS sin_fecha
        FROM fase f
        LEFT JOIN partido p ON p.fase_id = f.id
        WHERE f.torneo_id = %s
        GROUP BY f.id, f.nombre, f.tipo, f.orden, f.bloqueada
        HAVING COUNT(p.id) > 0
        ORDER BY f.orden, f.id
    """, (tid,))
    fases = cur.fetchall()
    print(f"\n=== {tnombre} (torneo {tid}) ===")
    for nombre, tipo, orden, bloq, total, sin_fecha in fases:
        estado = "OK" if sin_fecha == 0 else f"FALTAN {sin_fecha}/{total}"
        flag = "   " if sin_fecha == 0 else ">> "
        blq = " [bloqueada]" if bloq else ""
        print(f"{flag}{nombre:<28} ({tipo:<10}) total={total:<3} sin_fecha={sin_fecha:<3} -> {estado}{blq}")
        if sin_fecha:
            total_incompletas += 1
            cur.execute("""
                SELECT p.id,
                       COALESCE(el.nombre_es, el.nombre, '?'),
                       COALESCE(ev.nombre_es, ev.nombre, '?')
                FROM partido p
                LEFT JOIN equipo el ON el.id = p.equipo_local_id
                LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE p.fase_id = (SELECT id FROM fase WHERE torneo_id=%s AND nombre=%s AND tipo=%s LIMIT 1)
                  AND p.fecha IS NULL
                ORDER BY p.id
            """, (tid, nombre, tipo))
            for pid, ln, vn in cur.fetchall():
                print(f"       P{pid}: {ln} vs {vn}")

print(f"\n== Fases con partidos sin fecha: {total_incompletas} ==")
if total_incompletas:
    print("Sugerencia: inferir las fechas desde API-Football (ver inferir_fechas_*.py)")
