# -*- coding: utf-8 -*-
"""
cerrar_torneo_custom.py -- CIERRE con datos OFICIALES del usuario (sesion cowork).

Decisiones del usuario:
  - P104 (final Spain 1-0 Argentina): tarjetas OFICIALES = 6 amarillas, 1 roja
    (la API traia 5/2 -> se corrige a mano).
  - P103 (3er puesto France 4-6 England): tarjetas se dejan como la API (0/0).
  - Goleador global C = Mbappe. Se acredita a los 29 apostadores que le acertaron:
    se normalizan las predicciones 'MBAPPE'/variantes a 'KYLIAN MBAPPE' y se fija
    torneo.resultado_goleador = 'KYLIAN MBAPPE'.
  - Posiciones (Spain campeon, Argentina 2, England 3, France 4) YA correctas en BD.

NO hace sync (para no pisar las tarjetas corregidas). Requiere uvicorn en :8000.
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
GOLEADOR_OFICIAL = "KYLIAN MBAPPE"
CONN = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

conn = psycopg2.connect(CONN); conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 66)
print("BECBUC - CIERRE FINAL (datos oficiales del usuario)")
print("=" * 66)

# --- 1) Tarjetas oficiales de la final P104 ---
print("\n== 1) Tarjetas oficiales P104 (final): 6 amarillas, 1 roja ==")
cur.execute("""UPDATE partido SET amarillas=6, rojas=1
               WHERE id IN (SELECT p.id FROM partido p JOIN fase f ON f.id=p.fase_id
                            WHERE f.torneo_id=%s AND p.numero_fifa=104)""", (TID,))
print(f"   filas P104 actualizadas: {cur.rowcount}")
cur.execute("""SELECT numero_fifa, goles_local, goles_visitante, amarillas, rojas
               FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE f.torneo_id=%s AND p.numero_fifa IN (103,104) ORDER BY numero_fifa""", (TID,))
for r in cur.fetchall():
    print(f"   P{r['numero_fifa']}: {r['goles_local']}-{r['goles_visitante']}  amarillas={r['amarillas']}  rojas={r['rojas']}")

# --- 2) Goleador: normalizar predicciones a 'KYLIAN MBAPPE' y fijar oficial ---
print("\n== 2) Goleador global C -> Mbappe (acreditar a los 29) ==")
cur.execute("""SELECT TRIM(pred_goleador) AS g, COUNT(*) AS n FROM apuesta_global
               WHERE torneo_id=%s AND pred_goleador ILIKE '%%mbap%%'
               GROUP BY TRIM(pred_goleador) ORDER BY n DESC""", (TID,))
antes = cur.fetchall()
print("   grafías antes:", ", ".join(f"'{r['g']}'x{r['n']}" for r in antes))
cur.execute("""UPDATE apuesta_global SET pred_goleador=%s
               WHERE torneo_id=%s AND pred_goleador ILIKE '%%mbap%%'
                 AND UPPER(TRIM(pred_goleador)) <> %s""",
            (GOLEADOR_OFICIAL, TID, GOLEADOR_OFICIAL))
print(f"   predicciones normalizadas a '{GOLEADOR_OFICIAL}': {cur.rowcount}")
cur.execute("UPDATE torneo SET resultado_goleador=%s WHERE id=%s", (GOLEADOR_OFICIAL, TID))
cur.execute("""SELECT COUNT(*) AS n FROM apuesta_global
               WHERE torneo_id=%s AND LOWER(TRIM(pred_goleador))=LOWER(%s)""", (TID, GOLEADOR_OFICIAL))
print(f"   torneo.resultado_goleador='{GOLEADOR_OFICIAL}'  -> apostadores que matchean: {cur.fetchone()['n']}")

# --- 3) Recalcular puntajes forzando fases bloqueadas (SIN sync) ---
print("\n== 3) POST /calcular-puntajes/2?force_grupos=true (sin sync) ==")
lr = requests.post(f"{API_BASE}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=30)
tok = lr.json().get("access_token", "")
if not tok:
    sys.exit(f"login sin token -> {lr.status_code} {lr.text[:200]}")
hdr = {"Authorization": f"Bearer {tok}"}
cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TID}", headers=hdr,
                   params={"force_grupos": "true"}, timeout=600)
cd = cr.json()
if not cd.get("ok"):
    sys.exit(f"calcular-puntajes no OK -> {cd}")
print(f"   OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  globales_procesadas={cd.get('globales_procesadas')}")
for fase, d in (cd.get("por_fase") or {}).items():
    print(f"      [{fase:<14}] total={d.get('total',0):>6} apuestas={d.get('apuestas',0):>4}")

# --- 4) Marcar torneo cerrado ---
print("\n== 4) Marcar torneo cerrado ==")
cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado BOOLEAN DEFAULT FALSE")
cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado_at TIMESTAMPTZ")
cur.execute("UPDATE torneo SET cerrado=TRUE, cerrado_at=NOW() WHERE id=%s", (TID,))
print("   torneo.cerrado = TRUE")

# --- 5) Ranking final + globales ---
print("\n== 5) RANKING FINAL (top 15) ==")
rr = requests.get(f"{API_BASE}/bets/ranking/{TID}", headers=hdr, timeout=30)
_rj = rr.json(); rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
for i, ap in enumerate(rows[:15], 1):
    nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
    print(f"   {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
          f"(part={ap.get('puntos_partidos_total',0)}, glob={ap.get('pts_globales',0)})")

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
print("\n=== TORNEO CERRADO Y PUNTAJES FINALES CALCULADOS ===")
