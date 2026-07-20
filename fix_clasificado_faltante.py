# -*- coding: utf-8 -*-
"""
fix_clasificado_faltante.py [--apply]
Detecta partidos KO (P073-P104) FINALIZADOS con equipo_clasificado_id en NULL
e infiere el equipo que clasifica:
  - gana local/visitante por marcador -> ese equipo
  - empate -> por tanda de penales (penales_local vs penales_visitante)
  - empate sin tanda -> no se puede inferir (se reporta, no se toca)

SIN --apply: DRY RUN (muestra que setearia).
CON --apply: escribe equipo_clasificado_id en partido. Luego recalcular.

Uso:
  backend\.venv\Scripts\python.exe fix_clasificado_faltante.py
  backend\.venv\Scripts\python.exe fix_clasificado_faltante.py --apply
"""
import sys
DO_APPLY = '--apply' in [a.lower() for a in sys.argv[1:]]
print('[APPLY]' if DO_APPLY else '[DRY RUN]')
try:
    import psycopg2, psycopg2.extras
except ImportError:
    import os; os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
TID = 2
conn = psycopg2.connect(CONN); conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT p.numero_fifa, p.id, p.estado,
           p.equipo_local_id, el.nombre AS local, p.goles_local,
           p.equipo_visitante_id, ev.nombre AS visit, p.goles_visitante,
           p.penales_local, p.penales_visitante, p.equipo_clasificado_id
    FROM partido p JOIN fase f ON f.id=p.fase_id
    LEFT JOIN equipo el ON el.id=p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
    WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN 73 AND 104
    ORDER BY p.numero_fifa
""", (TID,))
rows = cur.fetchall()

updates = []; sin_inferir = []
print("\nKO finalizados con equipo_clasificado_id en NULL:")
for r in rows:
    if r['estado'] != 'finalizado':
        continue
    if r['equipo_clasificado_id'] is not None:
        continue
    gl, gv = r['goles_local'], r['goles_visitante']
    winner_id = winner_name = None
    motivo = ''
    if gl is not None and gv is not None and gl != gv:
        if gl > gv: winner_id, winner_name = r['equipo_local_id'], r['local']; motivo = f"marcador {gl}-{gv}"
        else:       winner_id, winner_name = r['equipo_visitante_id'], r['visit']; motivo = f"marcador {gl}-{gv}"
    elif r['penales_local'] is not None and r['penales_visitante'] is not None:
        if r['penales_local'] > r['penales_visitante']:
            winner_id, winner_name = r['equipo_local_id'], r['local']; motivo = f"tanda {r['penales_local']}-{r['penales_visitante']}"
        else:
            winner_id, winner_name = r['equipo_visitante_id'], r['visit']; motivo = f"tanda {r['penales_local']}-{r['penales_visitante']}"
    if winner_id:
        print(f"  P{r['numero_fifa']:03d}: {r['local']} {gl}-{gv} {r['visit']}  -> clasifica {winner_name}  ({motivo})")
        updates.append((r['id'], winner_id, r['numero_fifa'], winner_name))
    else:
        print(f"  P{r['numero_fifa']:03d}: {r['local']} {gl}-{gv} {r['visit']}  -> NO se puede inferir (empate sin tanda)")
        sin_inferir.append(r['numero_fifa'])

print(f"\nA setear: {len(updates)}   Sin inferir: {len(sin_inferir)}")
if not updates:
    print("Nada que arreglar (o ninguno inferible).")

if not DO_APPLY:
    print("\n[DRY RUN] No se escribio. Para aplicar: fix_clasificado_faltante.py --apply")
    conn.close(); sys.exit(0)

for pid_db, winner_id, nf, wname in updates:
    cur.execute("UPDATE partido SET equipo_clasificado_id=%s WHERE id=%s", (winner_id, pid_db))
    print(f"  P{nf:03d} -> {wname}  OK")
conn.commit()
print(f"\nOK. {len(updates)} partidos actualizados.")
print("AHORA recalcular: run_recalc_hasta_semis.bat")
conn.close()
