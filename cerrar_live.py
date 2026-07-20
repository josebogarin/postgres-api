# -*- coding: utf-8 -*-
"""
cerrar_live.py -- Cierre/recalculo del torneo con mensajes de avance y timestamps.
Pensado para correr en vivo:  python -u cerrar_live.py
Idempotente. NO hace sync (no pisa las tarjetas oficiales).
Datos oficiales de la final (P104): amarillas=6, rojas=1, penales=0, minuto_gol=106.
Goleador global C = KYLIAN MBAPPE (29 apostadores).
"""
import sys, os, time
from datetime import datetime
def log(msg): print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)

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

log("Conectando a Postgres (becbuc)...")
conn = psycopg2.connect(CONN); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
log("Conectado.")

log("1) Reafirmando P104 oficial: amarillas=6, rojas=1, penales=0, minuto_primer_gol=106")
cur.execute("""UPDATE partido SET amarillas=6, rojas=1, penales_partido=0, minuto_primer_gol=106
               WHERE id IN (SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id
                            WHERE f.torneo_id=%s AND p.numero_fifa=104)""", (TID,))
log(f"   P104 actualizado ({cur.rowcount} fila).")

log("2) Goleador C = KYLIAN MBAPPE (normalizando grafias + fijando resultado)")
cur.execute("""UPDATE apuesta_global SET pred_goleador=%s
               WHERE torneo_id=%s AND pred_goleador ILIKE '%%mbap%%' AND UPPER(TRIM(pred_goleador))<>%s""",
            (GOL, TID, GOL))
log(f"   predicciones normalizadas: {cur.rowcount}")
cur.execute("UPDATE torneo SET resultado_goleador=%s WHERE id=%s", (GOL, TID))
log("   torneo.resultado_goleador fijado.")

log("3) Login a la API...")
lr = requests.post(f"{API_BASE}/auth/login", json={"username":"jose","password":"catalina"}, timeout=30)
tok = lr.json().get("access_token","")
if not tok:
    log(f"   ERROR login: {lr.status_code} {lr.text[:150]}"); sys.exit(1)
hdr = {"Authorization": f"Bearer {tok}"}
log("   Login OK.")

log("4) POST /calcular-puntajes/2?force_grupos=true  (esto puede tardar; esperando respuesta del servidor)...")
t0 = time.time()
try:
    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TID}", headers=hdr,
                       params={"force_grupos":"true"}, timeout=300)
    dt = time.time()-t0
    cd = cr.json()
    log(f"   Respuesta en {dt:.1f}s -> ok={cd.get('ok')} plenos={cd.get('plenos')} aciertos={cd.get('aciertos')} globales={cd.get('globales_procesadas')}")
except requests.exceptions.Timeout:
    log(f"   *** TIMEOUT tras {time.time()-t0:.0f}s: el endpoint no respondio. Puede haber otro proceso Python ocupando uvicorn. ***")
    sys.exit(2)

log("5) Marcando torneo cerrado...")
cur.execute("UPDATE torneo SET cerrado=TRUE WHERE id=%s", (TID,))

log("6) Ranking final (top 15):")
rj = requests.get(f"{API_BASE}/bets/ranking/{TID}", headers=hdr, timeout=60).json()
rows = rj.get("ranking", []) if isinstance(rj, dict) else rj
for i, ap in enumerate(rows[:15], 1):
    nm = ap.get('apostador') or ap.get('username') or '?'
    print(f"     {i:>2}. {nm:<20} {ap.get('puntos_total',0):>6} pts  (part={ap.get('puntos_partidos_total',0)}, glob={ap.get('pts_globales',0)})", flush=True)

log("7) Globales: apostadores con puntaje>0 por item:")
for col,lbl in [("pts_campeon","A campeon"),("pts_finalistas","B finalistas"),("pts_goleador","C goleador"),
                ("pts_peor_equipo","D peor equipo"),("pts_mayor_goleada","E mayor goleada"),
                ("pts_etapa_paraguay","F etapa PY"),("pts_goles_paraguay","G goles PY")]:
    try:
        cur.execute(f"SELECT COUNT(*) AS n FROM puntaje_global WHERE torneo_id=%s AND COALESCE({col},0)>0",(TID,))
        print(f"     {lbl:<16}: {cur.fetchone()['n']}", flush=True)
    except Exception: pass
conn.close()
log("LISTO: torneo cerrado y puntajes finales calculados.")
