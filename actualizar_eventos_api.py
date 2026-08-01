import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
# -*- coding: utf-8 -*-
r"""
actualizar_eventos_api.py [numero_fifa | all]   (default 104)
Refresca SOLO la columna partido.eventos_api con los eventos EN VIVO de
API-Football (para que el timeline del live muestre el detalle correcto).
NO toca goles/amarillas/rojas/VAR ni ningún total (no altera el scoring).

  104   -> solo la final
  all   -> todos los partidos KO (numero_fifa 73..104) con api_fixture_id

Uso:  backend\.venv\Scripts\python.exe actualizar_eventos_api.py 104
      backend\.venv\Scripts\python.exe actualizar_eventos_api.py all
"""
import sys, os, re, json, time
ARG = (sys.argv[1] if len(sys.argv) > 1 else "104").lower()
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
KEY = None
for envp in (_osp.path.join(_BASE, 'backend', '.env'), _osp.path.join(_BASE, '.env')):
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
KEY = KEY or "f13bee776659e2c20c715a81ecff2307"

conn = psycopg2.connect(CONN); conn.autocommit = False
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

if ARG == "all":
    cur.execute("""SELECT p.numero_fifa, p.api_fixture_id
                   FROM partido p JOIN fase f ON f.id=p.fase_id
                   WHERE f.torneo_id=2 AND p.numero_fifa BETWEEN 73 AND 104
                     AND p.api_fixture_id IS NOT NULL ORDER BY p.numero_fifa""")
    targets = cur.fetchall()
else:
    cur.execute("""SELECT p.numero_fifa, p.api_fixture_id
                   FROM partido p JOIN fase f ON f.id=p.fase_id
                   WHERE f.torneo_id=2 AND p.numero_fifa=%s""", (int(ARG),))
    targets = cur.fetchall()

if not targets:
    sys.exit("Sin partidos con api_fixture_id para el criterio dado.")

print(f"Refrescando eventos_api de {len(targets)} partido(s)...")
ok = 0
for r in targets:
    nf, fix = r["numero_fifa"], r["api_fixture_id"]
    if not fix:
        print(f"  P{nf}: sin api_fixture_id, salteado"); continue
    try:
        resp = requests.get("https://v3.football.api-sports.io/fixtures",
                            params={"id": fix},
                            headers={"x-apisports-key": KEY}, timeout=30)
        data = resp.json()
        if resp.status_code != 200 or not data.get("response"):
            print(f"  P{nf}: API {resp.status_code} -> {str(data)[:120]}"); continue
        events = data["response"][0].get("events", [])
        cur.execute("UPDATE partido SET eventos_api = %s::jsonb WHERE api_fixture_id = %s",
                    (json.dumps(events), fix))
        conn.commit()
        n_card = sum(1 for e in events if e.get("type") == "Card")
        print(f"  P{nf}: {len(events)} eventos ({n_card} tarjetas) guardados")
        ok += 1
        time.sleep(0.4)
    except Exception as e:
        conn.rollback(); print(f"  P{nf}: ERROR {e}")

conn.close()
print(f"\nListo. Actualizados: {ok}. NO se tocó ningún total (goles/amarillas/rojas/VAR intactos).")
print("Recargá el live: el timeline ahora refleja los eventos en vivo de la API.")
