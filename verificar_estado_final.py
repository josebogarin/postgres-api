# -*- coding: utf-8 -*-
r"""
verificar_estado_final.py  (solo lectura)
Confirma el estado que muestra el live: torneo.cerrado, partidos finalizados,
filas de puntaje y ranking top 15 (mismo endpoint que usa el live).

Uso:  backend\.venv\Scripts\python.exe verificar_estado_final.py
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

API = "http://localhost:8000/api/v1"
TID = 2
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

print("=" * 60)
print("ESTADO FINAL (lo que refleja el live)")
print("=" * 60)

conn = psycopg2.connect(CONN); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("SELECT COALESCE(cerrado,FALSE) AS cerrado, cerrado_at FROM torneo WHERE id=%s", (TID,))
t = cur.fetchone()
print(f"\ntorneo.cerrado = {t['cerrado']}   (cerrado_at={t['cerrado_at']})")
cur.execute("""SELECT COUNT(*) FILTER (WHERE estado='finalizado') AS fin, COUNT(*) AS total
               FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s""", (TID,))
r = cur.fetchone()
print(f"Partidos finalizados: {r['fin']}/{r['total']}")
cur.execute("""SELECT COUNT(*) n FROM puntaje_detalle pd JOIN partido p ON p.id=pd.partido_id
               JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=%s""", (TID,))
print(f"Filas en puntaje_detalle: {cur.fetchone()['n']}")
conn.close()

try:
    lr = requests.post(f"{API}/auth/login", json={"username": "jose", "password": "catalina"}, timeout=20)
    tok = lr.json().get("access_token", "")
    hdr = {"Authorization": f"Bearer {tok}"}
    rr = requests.get(f"{API}/bets/ranking/{TID}", headers=hdr, timeout=30)
    rj = rr.json(); rows = rj.get("ranking", []) if isinstance(rj, dict) else rj
    print("\nRANKING top 15 (endpoint del live):")
    for i, ap in enumerate(rows[:15], 1):
        nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
        print(f"   {i:>2}. {nombre:<18} {ap.get('puntos_total', 0):>6} pts")
    print("\nEsperado: 1o checho 1077. Si coincide, el live esta OK (Ctrl+F5 en el navegador).")
except Exception as e:
    print(f"\n(No pude leer el ranking via API: {e}  -> uvicorn en :8000?)")
