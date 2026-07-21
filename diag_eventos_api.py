# -*- coding: utf-8 -*-
r"""
diag_eventos_api.py [numero_fifa]   (default 104)
Re-consulta la fixture EN VIVO en API-Football y vuelca sus tarjetas, para
comparar con lo que hay guardado en eventos_api (por si el snapshot quedó viejo).
Solo lectura. Consume 1 llamada de la cuota de API-Football.

Uso:  backend\.venv\Scripts\python.exe diag_eventos_api.py 104
"""
import sys, os, re
NF = int(sys.argv[1]) if len(sys.argv) > 1 else 104
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

# API key desde backend/.env (o raiz), fallback a la conocida.
KEY = None
for envp in (r"C:\proyecto FAST API\backend\.env", r"C:\proyecto FAST API\.env"):
    try:
        with open(envp, encoding="utf-8") as f:
            for line in f:
                m = re.match(r"\s*APIFOOTBALL_KEY\s*=\s*(.+)\s*", line)
                if m:
                    KEY = m.group(1).strip().strip('"').strip("'"); break
    except Exception:
        pass
    if KEY:
        break
if not KEY:
    KEY = "f13bee776659e2c20c715a81ecff2307"

conn = psycopg2.connect(CONN)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""SELECT p.api_fixture_id, el.nombre AS local, ev.nombre AS visit
               FROM partido p JOIN fase f ON f.id=p.fase_id
               LEFT JOIN equipo el ON el.id=p.equipo_local_id
               LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
               WHERE f.torneo_id=2 AND p.numero_fifa=%s""", (NF,))
r = cur.fetchone()
conn.close()
if not r or not r["api_fixture_id"]:
    sys.exit(f"P{NF} sin api_fixture_id (no se puede consultar la API).")
fix = r["api_fixture_id"]
print(f"P{NF}: {r['local']} vs {r['visit']}  (api_fixture_id={fix})")

resp = requests.get(
    "https://v3.football.api-sports.io/fixtures",
    params={"id": fix},
    headers={"x-apisports-key": KEY},
    timeout=30,
)
data = resp.json()
if resp.status_code != 200 or not data.get("response"):
    sys.exit(f"API respondio {resp.status_code}: {str(data)[:300]}")
events = data["response"][0].get("events", [])
print(f"\nEventos EN VIVO desde API-Football: {len(events)}")

def _min(e):
    el = (e.get("time") or {}).get("elapsed")
    ex = (e.get("time") or {}).get("extra")
    return f"{el}{('+'+str(ex)) if ex else ''}"

from collections import Counter
tipos = Counter(e.get("type", "") for e in events)
print("Conteo por tipo:", dict(tipos))

print("\n--- TODOS los eventos (en vivo) ---")
print(f"{'min':>5}  {'tipo':<8}{'detalle':<24}{'jugador':<26}{'pid':>7}  equipo")
for e in sorted(events, key=lambda x: ((x.get('time') or {}).get('elapsed') or 0)):
    pl = (e.get("player") or {})
    print(f"{_min(e):>5}  {e.get('type',''):<8}{e.get('detail',''):<24}"
          f"{(pl.get('name') or '—'):<26}{str(pl.get('id')):>7}  {((e.get('team') or {}).get('name'))}")

print("\n--- Tarjetas (Card) ---")
for e in events:
    if e.get("type") == "Card":
        pl = (e.get("player") or {})
        print(f"  {_min(e):>5}'  {e.get('detail',''):<22} {pl.get('name') or '—'} (pid={pl.get('id')})  {((e.get('team') or {}).get('name'))}")

print("\n--- VAR (Var) ---")
_var = [e for e in events if e.get("type") == "Var"]
if _var:
    for e in _var:
        print(f"  {_min(e):>5}'  {e.get('detail','')}  {((e.get('team') or {}).get('name'))}")
else:
    print("  (la API tampoco trae eventos 'Var' para esta fixture)")

print("\n=> Si aca aparece la 2a amarilla de Enzo (Second Yellow card) o eventos Var,")
print("   el snapshot guardado quedo viejo -> re-sincronizar actualiza eventos_api.")
print("   Si NO aparecen, ese dato no existe en API-Football para esta fixture.")
