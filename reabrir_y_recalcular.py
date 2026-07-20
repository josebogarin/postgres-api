# -*- coding: utf-8 -*-
r"""
reabrir_y_recalcular.py  [--no-recerrar]

Reabre el torneo 2, recalcula TODOS los puntajes (fuerza fases bloqueadas) y lo
vuelve a cerrar. NO hace sync desde API-Football (respeta los resultados oficiales
cargados a mano; el sync los pisaria).

Pasos:
  1) torneo.cerrado = FALSE            (reabrir)
  2) POST /calcular-puntajes/2?force_grupos=true   (reconstruye puntaje_detalle
     de las 104 partidos + recalcula globales A-G ; LENTO 1-3 min)
  3) torneo.cerrado = TRUE             (re-cerrar; omitir con --no-recerrar)
  4) Ranking final top 15 + globales con puntaje > 0

Requiere uvicorn en :8000 (jose/catalina) y Docker (becbuc).
Uso:
  backend\.venv\Scripts\python.exe reabrir_y_recalcular.py
  backend\.venv\Scripts\python.exe reabrir_y_recalcular.py --no-recerrar
"""
import sys, os
RECERRAR = '--no-recerrar' not in [a.lower() for a in sys.argv[1:]]

try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

API_BASE = "http://localhost:8000/api/v1"
API_USER, API_PASS = "jose", "catalina"
TID = 2
CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

def db():
    c = psycopg2.connect(CONN_BEC); c.autocommit = True
    return c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 68)
print("BECBUC - REABRIR + RECALCULAR + RE-CERRAR  (torneo 2)")
print("=" * 68)

conn, cur = db()

# login
lr = requests.post(f"{API_BASE}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=30)
tok = lr.json().get("access_token", "")
if not tok:
    sys.exit(f"login sin token -> {lr.status_code} {lr.text[:200]}\n(uvicorn en :8000?)")
hdr = {"Authorization": f"Bearer {tok}"}

# 1) reabrir
print("\n== 1) Reabrir torneo (cerrado=FALSE) ==")
cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado BOOLEAN DEFAULT FALSE")
cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado_at TIMESTAMPTZ")
cur.execute("UPDATE torneo SET cerrado=FALSE WHERE id=%s", (TID,))
print("   torneo.cerrado = FALSE")

# 2) recalcular (fuerza fases bloqueadas, reconstruye TODO)
print("\n== 2) POST /calcular-puntajes/2?force_grupos=true  (LENTO, esperar 1-3 min) ==")
try:
    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TID}", headers=hdr,
                       params={"force_grupos": "true"}, timeout=900)
    cd = cr.json()
except Exception as e:
    sys.exit(f"   ERROR en calcular-puntajes: {e}")
if not cd.get("ok"):
    sys.exit(f"   calcular-puntajes no OK -> {cd}")
print(f"   OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  "
      f"globales_procesadas={cd.get('globales_procesadas')}")
for fase, d in (cd.get("por_fase") or {}).items():
    print(f"      [{fase:<14}] total={d.get('total',0):>6}  apuestas={d.get('apuestas',0):>4}")

# 3) re-cerrar
if RECERRAR:
    print("\n== 3) Re-cerrar torneo (cerrado=TRUE) ==")
    cur.execute("UPDATE torneo SET cerrado=TRUE, cerrado_at=NOW() WHERE id=%s", (TID,))
    print("   torneo.cerrado = TRUE")
else:
    print("\n== 3) (--no-recerrar) el torneo queda ABIERTO ==")

# 4) ranking final
print("\n== 4) RANKING FINAL (top 15) ==")
try:
    rr = requests.get(f"{API_BASE}/bets/ranking/{TID}", headers=hdr, timeout=60)
    _rj = rr.json(); rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
    for i, ap in enumerate(rows[:15], 1):
        nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
        print(f"   {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
              f"(part={ap.get('puntos_partidos_total',0)}, glob={ap.get('pts_globales',0)})")
except Exception as e:
    print(f"   (no pude leer ranking: {e})")

print("\n== Globales: apostadores con puntaje > 0 por item ==")
for col, lbl in [("pts_campeon","A campeon"),("pts_finalistas","B finalistas"),
                 ("pts_goleador","C goleador"),("pts_peor_equipo","D peor equipo"),
                 ("pts_mayor_goleada","E mayor goleada"),
                 ("pts_etapa_paraguay","F etapa PY"),("pts_goles_paraguay","G goles PY")]:
    try:
        cur.execute(f"SELECT COUNT(*) AS n FROM puntaje_global WHERE torneo_id=%s AND COALESCE({col},0)>0", (TID,))
        print(f"   {lbl:<16}: {cur.fetchone()['n']}")
    except Exception:
        pass

conn.close()
print("\n=== LISTO. Puntajes recalculados"
      + (" y torneo cerrado. ===" if RECERRAR else " (torneo abierto). ==="))
