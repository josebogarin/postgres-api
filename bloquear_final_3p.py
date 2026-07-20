# -*- coding: utf-8 -*-
"""
bloquear_final_3p.py [--apply]
Bloquea las fases FINAL y TERCER PUESTO del torneo 2 (fase.bloqueada=TRUE).
Con esto el editor "Mi Prono" de becbuc-live-playoffs.html deja de mostrar partidos
editables (cierra la carga/edicion de apuestas) y el backend rechaza cualquier guardado.

SIN --apply: DRY RUN (muestra estado actual, no escribe).
CON --apply: bloquea las fases.

NOTA: al bloquear, calcular-puntajes SALTA esas fases. Cuando P103/P104 se jueguen,
      para puntuarlas usar run_recalc_force_grupos.bat (force_grupos=true reconstruye
      TODO incluidas fases bloqueadas, sin tocar el estado de bloqueo).
Solo BD (psycopg2).
"""
import sys, os
DO_APPLY = '--apply' in [a.lower() for a in sys.argv[1:]]
print(f"{'[APPLY]' if DO_APPLY else '[DRY RUN]'}")
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TID = 2
TIPOS = ('final', 'tercer_puesto', 'tercero', 'semis')

conn = psycopg2.connect(CONN_BEC); conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def dump():
    cur.execute("""SELECT id, nombre, tipo, COALESCE(bloqueada,FALSE) AS bloqueada
                   FROM fase WHERE torneo_id=%s ORDER BY id""", (TID,))
    print(f"\n{'ID':>4}  {'TIPO':<16}{'NOMBRE':<26}{'BLOQUEADA'}")
    for f in cur.fetchall():
        print(f"{f['id']:>4}  {f['tipo']:<16}{(f['nombre'] or ''):<26}{'SI' if f['bloqueada'] else 'no'}")

print("== Estado ANTES ==")
dump()

# fases objetivo
cur.execute("""SELECT id, nombre, tipo, COALESCE(bloqueada,FALSE) AS bloqueada
               FROM fase WHERE torneo_id=%s AND lower(tipo) IN %s""", (TID, TIPOS))
objetivo = cur.fetchall()
pendientes = [f for f in objetivo if not f['bloqueada']]
print(f"\nFases Final/3er puesto: {[(f['tipo'], 'SI' if f['bloqueada'] else 'no') for f in objetivo]}")
print(f"A bloquear: {[f['nombre'] for f in pendientes]}")

if DO_APPLY and pendientes:
    cur.execute("""UPDATE fase SET bloqueada=TRUE
                   WHERE torneo_id=%s AND lower(tipo) IN %s""", (TID, TIPOS))
    conn.commit()
    print(f"\n[APPLY] Fases bloqueadas: {cur.rowcount}")
    print("== Estado DESPUES ==")
    dump()
    print("\nEditor de apuestas CERRADO. El backend rechaza guardados en estas fases.")
elif pendientes:
    print("\n[DRY RUN] No se escribio. Para aplicar: bloquear_final_3p.py --apply")
else:
    print("\nNada que bloquear (ya estaban bloqueadas).")
conn.close()
