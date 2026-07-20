# -*- coding: utf-8 -*-
"""
swap_apuestas.py
Intercambia las PREDICCIONES entre dos apostadores para un rango de partidos
(por numero_fifa). Mantiene apostador_id y nombre; solo permuta los campos pred_*.
Sirve para corregir apuestas cruzadas por error del Excel.

Uso:
  python swap_apuestas.py san pato 89 96            <- DRY RUN octavos
  python swap_apuestas.py san pato 89 96 --apply    <- aplica el swap
  python swap_apuestas.py san pato 97 100 --apply   <- cuartos (si hiciera falta)
"""
import sys, os
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

args = [a for a in sys.argv[1:] if not a.startswith('--')]
if len(args) < 4:
    sys.exit("Uso: python swap_apuestas.py <user1> <user2> <nf_desde> <nf_hasta> [--apply]")
U1, U2 = args[0].lower(), args[1].lower()
NF_A, NF_B = int(args[2]), int(args[3])
APPLY = '--apply' in sys.argv
TORNEO_ID = 2

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
CONN_APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"

PRED_COLS = [
    "pred_local", "pred_visitante", "pred_amarillas", "pred_rojas", "pred_var",
    "pred_penales_partido", "pred_minuto_gol", "pred_penales_local_tanda",
    "pred_penales_visitante_tanda", "pred_equipo_clasifica",
]

conn_bec = psycopg2.connect(CONN_BEC); conn_app = psycopg2.connect(CONN_APP)
cur_bec = conn_bec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur_app = conn_app.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Resolver apostador_ids ────────────────────────────────────────────────────
cur_app.execute("SELECT id, username, COALESCE(nombre,'') AS nombre FROM users WHERE lower(username) IN (%s,%s)", (U1, U2))
found = {r['username'].lower(): r for r in cur_app.fetchall()}
if U1 not in found or U2 not in found:
    print("Usuarios encontrados:", {k: (v['id'], v['nombre']) for k, v in found.items()})
    # Ayuda: listar candidatos
    cur_app.execute("SELECT id, username, nombre FROM users WHERE username ILIKE %s OR username ILIKE %s OR nombre ILIKE %s OR nombre ILIKE %s",
                    (f'%{U1}%', f'%{U2}%', f'%{U1}%', f'%{U2}%'))
    print("Candidatos:", [(r['username'], r['nombre']) for r in cur_app.fetchall()])
    sys.exit(f"ERROR: no se resolvieron ambos usuarios ({U1}, {U2}).")
id1, id2 = found[U1]['id'], found[U2]['id']
print(f"{U1} -> id={id1} ({found[U1]['nombre']})")
print(f"{U2} -> id={id2} ({found[U2]['nombre']})")

# ── Partidos del rango ────────────────────────────────────────────────────────
cur_bec.execute("""
    SELECT p.id, p.numero_fifa FROM partido p JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN %s AND %s ORDER BY p.numero_fifa
""", (TORNEO_ID, NF_A, NF_B))
partidos = {r['id']: r['numero_fifa'] for r in cur_bec.fetchall()}
print(f"\nPartidos en rango P{NF_A:03d}-P{NF_B:03d}: {len(partidos)}")

# ── Leer apuestas de ambos ────────────────────────────────────────────────────
cols_sql = ", ".join(PRED_COLS)
def load(uid):
    cur_bec.execute(f"SELECT partido_id, {cols_sql} FROM apuesta WHERE apostador_id=%s AND partido_id = ANY(%s)",
                    (uid, list(partidos.keys())))
    return {r['partido_id']: dict(r) for r in cur_bec.fetchall()}
ap1, ap2 = load(id1), load(id2)

print(f"\n{'partido':<8}{U1:<40}{U2}")
for pid in sorted(partidos, key=lambda x: partidos[x]):
    nf = partidos[pid]
    a = ap1.get(pid); b = ap2.get(pid)
    def brief(x):
        if not x: return "(sin apuesta)"
        return f"{x['pred_local']}-{x['pred_visitante']} J{x['pred_amarillas']} K{x['pred_rojas']} L{x['pred_var']} M{x['pred_penales_partido']} N{x['pred_minuto_gol']} T{x['pred_penales_local_tanda']}/{x['pred_penales_visitante_tanda']} Cls{x['pred_equipo_clasifica']}"
    print(f"P{nf:03d}    {brief(a):<40}{brief(b)}")

if not APPLY:
    print("\n[DRY RUN] No se modifico nada. Para intercambiar: agrega --apply")
    sys.exit(0)

# ── Swap atomico ──────────────────────────────────────────────────────────────
print("\nAplicando swap...")
set_clause = ", ".join(f"{c}=%s" for c in PRED_COLS)
swapped = 0
for pid in partidos:
    a = ap1.get(pid); b = ap2.get(pid)
    if not a or not b:
        print(f"  P{partidos[pid]:03d}: uno de los dos no tiene apuesta -> se omite")
        continue
    # id1 recibe valores de b (U2); id2 recibe valores de a (U1)
    cur_bec.execute(f"UPDATE apuesta SET {set_clause} WHERE apostador_id=%s AND partido_id=%s",
                    [b[c] for c in PRED_COLS] + [id1, pid])
    cur_bec.execute(f"UPDATE apuesta SET {set_clause} WHERE apostador_id=%s AND partido_id=%s",
                    [a[c] for c in PRED_COLS] + [id2, pid])
    swapped += 1
conn_bec.commit()
print(f"Swap aplicado en {swapped} partidos.")

# ── Verificacion ──────────────────────────────────────────────────────────────
ap1b, ap2b = load(id1), load(id2)
ok = all(ap1b[pid]['pred_local']==ap2[pid]['pred_local'] and ap2b[pid]['pred_local']==ap1[pid]['pred_local']
         for pid in partidos if pid in ap1 and pid in ap2)
print("Verificacion swap:", "OK" if ok else "REVISAR")
print("\nRecalcular puntajes: POST /calcular-puntajes/2 (si estos partidos ya estan finalizados).")
conn_bec.close(); conn_app.close()
