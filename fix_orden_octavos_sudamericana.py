# -*- coding: utf-8 -*-
"""
fix_orden_octavos_sudamericana.py - Corrige el ORDEN de las llaves de octavos
del torneo 14 para que el arbol converja bien. Reinserta las llaves sembradas
1-4 (Recoleta, At.Mineiro, Botafogo, Olimpia) en sus ids ORIGINALES 3584-3591
(que quedaron libres), preservando los equipos ya resueltos. No toca las 5-8.

Uso:  python fix_orden_octavos_sudamericana.py            (DRY-RUN)
      python fix_orden_octavos_sudamericana.py --apply
"""
import sys, psycopg2

APPLY = "--apply" in sys.argv
TID = 14
SEED_ORDER = ["Recoleta", "Atletico Mineiro", "Botafogo", "Olimpia"]   # llaves 1-4, en orden
TARGET_IDS = [3584, 3585, 3586, 3587, 3588, 3589, 3590, 3591]          # ida,vuelta x4

conn = psycopg2.connect(host="localhost", port=5432, dbname="becbuc",
                        user="app_user", password="superpassword")
cur = conn.cursor()

cur.execute("SELECT id FROM fase WHERE torneo_id=%s AND tipo='ronda16'", (TID,))
fase_id = cur.fetchone()[0]

def eq_id(n):
    cur.execute("SELECT id FROM equipo WHERE nombre=%s OR nombre_es=%s ORDER BY id LIMIT 1",(n,n))
    r=cur.fetchone(); return r[0] if r else None

seed_ids = {n: eq_id(n) for n in SEED_ORDER}

# Partidos actuales de octavos que involucran a las seeds 1-4
cur.execute("""SELECT p.id, p.equipo_local_id, el.nombre, p.equipo_visitante_id, ev.nombre,
                      p.sede, p.ciudad, p.estado
               FROM partido p JOIN equipo el ON el.id=p.equipo_local_id
                              JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE p.fase_id=%s ORDER BY p.id""", (fase_id,))
rows=cur.fetchall()

# Agrupar por seed (una seed puede estar de local o visitante)
por_seed = {n: [] for n in SEED_ORDER}
otros = []
for pid,lid,ln,vid,vn,sede,ciudad,est in rows:
    hit=None
    for n in SEED_ORDER:
        if seed_ids[n] in (lid, vid): hit=n; break
    if hit: por_seed[hit].append((pid,lid,ln,vid,vn,sede,ciudad,est))
    else: otros.append((pid,lid,ln,vid,vn,sede,ciudad,est))

print("Fase octavos id=", fase_id)
print("\n-- Llaves 1-4 actuales (a reinsertar con id original) --")
plan=[]
free_ok=True
# chequear ids objetivo libres
cur.execute(f"SELECT id FROM partido WHERE id IN ({','.join(map(str,TARGET_IDS))})")
ocupados=[r[0] for r in cur.fetchall()]
if ocupados:
    print(f"  OJO: ids objetivo ya ocupados: {ocupados} -> NO se puede reinsertar limpio."); free_ok=False

for i,n in enumerate(SEED_ORDER):
    legs=por_seed[n]
    if len(legs)!=2:
        print(f"  {n}: se esperaban 2 piernas, hay {len(legs)} -> revisar"); free_ok=False; continue
    # ida = rival local (seed visitante); vuelta = seed local
    ida = next((L for L in legs if L[1]!=seed_ids[n]), None)   # local != seed
    vue = next((L for L in legs if L[1]==seed_ids[n]), None)   # local == seed
    if not ida or not vue:
        print(f"  {n}: no distingo ida/vuelta -> revisar"); free_ok=False; continue
    ida_id, vue_id = TARGET_IDS[2*i], TARGET_IDS[2*i+1]
    # ida: local=rival, visit=seed ; vuelta: local=seed, visit=rival
    rival_id = ida[1]  # local de la ida = rival ya resuelto
    print(f"  llave {i+1} {n}: nuevo id ida={ida_id} (local={ida[2]} vs {ida[4]}), "
          f"vuelta={vue_id} (local={vue[2]} vs {vue[4]})  [borra {ida[0]},{vue[0]}]")
    plan.append((n, ida, vue, ida_id, vue_id, rival_id, seed_ids[n]))

if not APPLY:
    print("\n== DRY-RUN (agrega --apply) ==")
    cur.close(); conn.close(); sys.exit(0)

if not free_ok:
    print("\nNo aplico: hay inconsistencias arriba."); cur.close(); conn.close(); sys.exit(1)

# Borrar los actuales de seeds 1-4 y reinsertar con id explicito
old_ids=[]
for n,ida,vue,ida_id,vue_id,rival_id,sid in plan:
    old_ids += [ida[0], vue[0]]
in_sql="("+",".join(map(str,old_ids))+")"
cur.execute(f"DELETE FROM partido WHERE id IN {in_sql}")

for n,ida,vue,ida_id,vue_id,rival_id,sid in plan:
    # ida: rival local, seed visitante
    cur.execute("""INSERT INTO partido (id, fase_id, torneo_id, equipo_local_id, equipo_visitante_id,
                   estado, sede, ciudad) OVERRIDING SYSTEM VALUE VALUES (%s,%s,%s,%s,%s,'programado',%s,%s)""",
                (ida_id, fase_id, TID, rival_id, sid, ida[5], ida[6]))
    # vuelta: seed local, rival visitante
    cur.execute("""INSERT INTO partido (id, fase_id, torneo_id, equipo_local_id, equipo_visitante_id,
                   estado, sede, ciudad) OVERRIDING SYSTEM VALUE VALUES (%s,%s,%s,%s,%s,'programado',%s,%s)""",
                (vue_id, fase_id, TID, sid, rival_id, vue[5], vue[6]))
    print(f"  reinsertada llave {n}: ida id={ida_id}, vuelta id={vue_id}")

conn.commit()
print("\n== COMMIT ok ==")
cur.close(); conn.close()
