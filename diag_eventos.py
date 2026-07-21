# -*- coding: utf-8 -*-
r"""
diag_eventos.py [numero_fifa]   (default 104 = final)
Vuelca los eventos crudos (eventos_api) de un partido para ver qué trae la API:
tipo, detalle, minuto, jugador (id/nombre), equipo. Solo lectura.

Uso:  backend\.venv\Scripts\python.exe diag_eventos.py 104
"""
import sys, json
try:
    import psycopg2, psycopg2.extras
except ImportError:
    import os
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet')
    import psycopg2, psycopg2.extras

NF = int(sys.argv[1]) if len(sys.argv) > 1 else 104
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

conn = psycopg2.connect(CONN)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT p.numero_fifa, el.nombre AS local, ev.nombre AS visit,
           el.api_team_id AS local_api, ev.api_team_id AS visit_api,
           p.amarillas, p.rojas, p.decisiones_var, p.penales_partido,
           p.eventos_api::text AS ev
    FROM partido p JOIN fase f ON f.id=p.fase_id
    LEFT JOIN equipo el ON el.id=p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
    WHERE f.torneo_id=2 AND p.numero_fifa=%s
""", (NF,))
r = cur.fetchone()
if not r:
    sys.exit(f"No existe P{NF}")

print(f"P{NF}: {r['local']} (api {r['local_api']}) vs {r['visit']} (api {r['visit_api']})")
print(f"BD totales -> amarillas={r['amarillas']} rojas={r['rojas']} "
      f"VAR={r['decisiones_var']} penales_juego={r['penales_partido']}")

try:
    evs = json.loads(r["ev"]) if r["ev"] else []
except Exception as e:
    sys.exit(f"eventos_api no parseable: {e}")

print(f"\nTotal eventos en eventos_api: {len(evs)}")
print(f"{'min':>5}  {'tipo':<8}{'detalle':<22}{'jugador':<26}{'pid':>7}  equipo")
tipos = {}
for e in evs:
    t = e.get("type", "")
    tipos[t] = tipos.get(t, 0) + 1
    el = (e.get("time") or {}).get("elapsed")
    ex = (e.get("time") or {}).get("extra")
    minu = f"{el}{('+'+str(ex)) if ex else ''}"
    det = e.get("detail", "")
    pl = (e.get("player") or {})
    tm = (e.get("team") or {})
    print(f"{minu:>5}  {t:<8}{det:<22}{(pl.get('name') or '—'):<26}{str(pl.get('id')):>7}  {tm.get('name','')}")

print("\nConteo por tipo:", tipos)
print("\n--- Solo tarjetas (Card) ---")
for e in evs:
    if e.get("type") == "Card":
        el = (e.get("time") or {}).get("elapsed")
        pl = (e.get("player") or {})
        print(f"  {el:>4}'  {e.get('detail',''):<22} {pl.get('name') or '—'} (pid={pl.get('id')})  {((e.get('team') or {}).get('name'))}")
print("\n--- Solo VAR (Var) ---")
_var = [e for e in evs if e.get("type") == "Var"]
if _var:
    for e in _var:
        el = (e.get("time") or {}).get("elapsed")
        print(f"  {el:>4}'  {e.get('detail','')}")
else:
    print("  (ninguno en eventos_api — el VAR vino de fuente secundaria)")
conn.close()
