# -*- coding: utf-8 -*-
"""
verify_final_tarjetas.py -- PRE-CIERRE: fuerza sync desde API-Football y muestra
los items reales de P103 (3er puesto) y P104 (final) para verificar tarjetas
(esperado por el usuario: 6 amarillas, 1 roja en la final).
Requiere uvicorn en :8000. NO cierra el torneo.
"""
import sys, os
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

print("=" * 60)
print("VERIFICACION TARJETAS FINAL (P103/P104) - sync API + lectura")
print("=" * 60)

# login
lr = requests.post(f"{API_BASE}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=30)
tok = lr.json().get("access_token", "")
if not tok:
    sys.exit(f"login sin token -> {lr.status_code} {lr.text[:200]}")
hdr = {"Authorization": f"Bearer {tok}"}

print("\n-- Sync desde API-Football (force) --")
try:
    sr = requests.post(f"{API_BASE}/bets/sync-resultados/{TID}", headers=hdr,
                       params={"force": "true", "max_detalle": 60}, timeout=600)
    sd = sr.json()
    print(f"   actualizados={sd.get('actualizados')}  bracket_ok={sd.get('bracket_ok')}  puntajes_ok={sd.get('puntajes_ok')}")
except Exception as e:
    print(f"   (sync error: {e})")

conn = psycopg2.connect(CONN_BEC); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""SELECT p.* FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE f.torneo_id=%s AND numero_fifa IN (103,104)
               ORDER BY numero_fifa""", (TID,))
print("\n-- Items en BD tras sync --")
for r in cur.fetchall():
    minuto = None
    for k in r.keys():
        if 'minuto' in k.lower():
            minuto = f"{k}={r[k]}"
    equipo_clas = r.get('equipo_clasificado_id')
    print(f"   P{r['numero_fifa']} [{r['estado']}] {r['goles_local']}-{r['goles_visitante']}  "
          f"amarillas={r.get('amarillas')}  rojas={r.get('rojas')}  VAR={r.get('decisiones_var')}  "
          f"pen_partido={r.get('penales_partido')}  clasificado_id={equipo_clas}  {minuto or ''}")
conn.close()
print("\n=== FIN VERIFICACION (torneo NO cerrado) ===")
