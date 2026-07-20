# -*- coding: utf-8 -*-
"""recalc_ranking.py -- Reafirma datos oficiales de la final, recalcula (force) y muestra ranking.
Idempotente. Sin sync (no pisa tarjetas). python -u para salida inmediata."""
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
TID = 2
GOL = "KYLIAN MBAPPE"
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

conn = psycopg2.connect(CONN); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print(">> Reafirmando P104 oficial: amarillas=6, rojas=1, penales=0, minuto_primer_gol=106", flush=True)
cur.execute("""UPDATE partido SET amarillas=6, rojas=1, penales_partido=0, minuto_primer_gol=106
               WHERE id IN (SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id
                            WHERE f.torneo_id=%s AND p.numero_fifa=104)""", (TID,))
print(f"   P104 filas: {cur.rowcount}", flush=True)
cur.execute("""UPDATE apuesta_global SET pred_goleador=%s
               WHERE torneo_id=%s AND pred_goleador ILIKE '%%mbap%%' AND UPPER(TRIM(pred_goleador))<>%s""",
            (GOL, TID, GOL))
cur.execute("UPDATE torneo SET resultado_goleador=%s WHERE id=%s", (GOL, TID))

print(">> login + calcular-puntajes force_grupos", flush=True)
tok = requests.post(f"{API_BASE}/auth/login", json={"username":"jose","password":"catalina"}, timeout=30).json().get("access_token","")
hdr = {"Authorization": f"Bearer {tok}"}
cd = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TID}", headers=hdr, params={"force_grupos":"true"}, timeout=600).json()
print(f"   calcular ok={cd.get('ok')} plenos={cd.get('plenos')} aciertos={cd.get('aciertos')} globales={cd.get('globales_procesadas')}", flush=True)

cur.execute("UPDATE torneo SET cerrado=TRUE WHERE id=%s", (TID,))

print("\n== RANKING FINAL (top 15) ==", flush=True)
rj = requests.get(f"{API_BASE}/bets/ranking/{TID}", headers=hdr, timeout=60).json()
rows = rj.get("ranking", []) if isinstance(rj, dict) else rj
for i, ap in enumerate(rows[:15], 1):
    nm = ap.get('apostador') or ap.get('username') or '?'
    print(f"   {i:>2}. {nm:<20} {ap.get('puntos_total',0):>6} pts  (part={ap.get('puntos_partidos_total',0)}, glob={ap.get('pts_globales',0)})", flush=True)

print("\n== Globales: apostadores con puntaje>0 ==", flush=True)
for col,lbl in [("pts_campeon","A campeon"),("pts_finalistas","B finalistas"),("pts_goleador","C goleador"),
                ("pts_peor_equipo","D peor equipo"),("pts_mayor_goleada","E mayor goleada"),
                ("pts_etapa_paraguay","F etapa PY"),("pts_goles_paraguay","G goles PY")]:
    try:
        cur.execute(f"SELECT COUNT(*) AS n FROM puntaje_global WHERE torneo_id=%s AND COALESCE({col},0)>0",(TID,))
        print(f"   {lbl:<16}: {cur.fetchone()['n']}", flush=True)
    except Exception: pass
conn.close()
print("\n=== LISTO: torneo cerrado y puntajes finales ===", flush=True)
