# -*- coding: utf-8 -*-
"""
cerrar_torneo_final.py  -- CIERRE DEL TORNEO (correr tras la Final P104 + 3er puesto P103)

TRIGGER DE EXCEPCION: con TODAS las fases bloqueadas, calcular-puntajes salta las
fases; este script fuerza el cierre completo:

  0) Verifica el estado: fases bloqueadas + P103/P104 finalizados.
  1) SIN ITEMS NULL: fuerza sync desde API-Football (import de todos los items + marcador)
     y luego chequea que NINGUN partido finalizado quede con items en null. Si quedan,
     reintenta el sync y reporta lo que la API no devolvio.
  2) GOLEADOR (global C): recalcula la tabla de goleadores (goleadores_cache) via el sync,
     toma el/los primeros por goles y asigna el goleador a torneo.resultado_goleador.
     (El engine compara C exacto case-insensitive: el nombre debe coincidir con lo que
      escribieron los apostadores.)
  3) FUERZA PUNTAJES: POST /calcular-puntajes/2?force_grupos=true -> puntua final/3er puesto
     (fases bloqueadas) + recalcula TODOS los globales A-G finales.
  4) Marca torneo.cerrado=TRUE (para el banner del live).
  5) Ranking final + resumen de globales + cuantos acertaron el goleador.

Requiere uvicorn en :8000. NO cambia el estado de bloqueo de las fases.
Uso: backend\\.venv\\Scripts\\python.exe cerrar_torneo_final.py
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

# items que un partido finalizado NO deberia tener en null
ITEMS_OBLIG = ["goles_local", "goles_visitante", "amarillas", "rojas",
               "decisiones_var", "penales_partido"]

def db():
    c = psycopg2.connect(CONN_BEC); c.autocommit = True
    return c, c.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("=" * 68)
print("BECBUC - CIERRE DEL TORNEO (final + 3er puesto)")
print("=" * 68)

conn, cur = db()

# 0) Estado
print("\n== 0) Estado de fases y partidos finales ==")
cur.execute("""SELECT tipo, COALESCE(bloqueada,FALSE) AS b FROM fase WHERE torneo_id=%s""", (TID,))
fases = cur.fetchall()
n_abiertas = sum(1 for f in fases if not f['b'])
print(f"   Fases: {len(fases)}  |  abiertas: {n_abiertas}  |  bloqueadas: {len(fases)-n_abiertas}")
cur.execute("""SELECT numero_fifa, estado, goles_local, goles_visitante
               FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE f.torneo_id=%s AND numero_fifa IN (103,104) ORDER BY numero_fifa""", (TID,))
for r in cur.fetchall():
    print(f"   P{r['numero_fifa']}: {r['estado']}  {r['goles_local']}-{r['goles_visitante']}")

# login
lr = requests.post(f"{API_BASE}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=30)
tok = lr.json().get("access_token", "")
if not tok: sys.exit(f"login sin token -> {lr.status_code} {lr.text[:200]}")
hdr = {"Authorization": f"Bearer {tok}"}

def nulls_pendientes():
    cond = " OR ".join(f"{c} IS NULL" for c in ITEMS_OBLIG)
    cur.execute(f"""SELECT numero_fifa, estado, {', '.join(ITEMS_OBLIG)}
                    FROM partido p JOIN fase f ON f.id=p.fase_id
                    WHERE f.torneo_id=%s AND estado='finalizado' AND ({cond})
                    ORDER BY numero_fifa""", (TID,))
    return cur.fetchall()

# 1) Sin items null: forzar sync
print("\n== 1) Import de items desde API-Football (force) ==")
def do_sync():
    try:
        sr = requests.post(f"{API_BASE}/bets/sync-resultados/{TID}", headers=hdr,
                           params={"force": "true", "max_detalle": 60}, timeout=600)
        sd = sr.json()
        print(f"   actualizados={sd.get('actualizados')}  bracket_ok={sd.get('bracket_ok')}  puntajes_ok={sd.get('puntajes_ok')}")
    except Exception as e:
        print(f"   (sync sin cambios o error: {e})")
do_sync()
faltan = nulls_pendientes()
if faltan:
    print(f"   Quedan {len(faltan)} partidos finalizados con items en null -> reintento sync...")
    do_sync()
    faltan = nulls_pendientes()
if faltan:
    print("   *** ATENCION: items en null que la API no devolvio (revisar manual): ***")
    for r in faltan:
        nn = [c for c in ITEMS_OBLIG if r[c] is None]
        print(f"      P{r['numero_fifa']}: null en {nn}")
else:
    print("   OK: ningun partido finalizado tiene items en null.")

# 2) Goleador global (C): tomar el/los primeros de goleadores_cache
print("\n== 2) Goleador global (C) desde la tabla de goleadores ==")
cur.execute("""SELECT nombre, goles FROM goleadores_cache WHERE torneo_id=%s
               ORDER BY goles DESC, posicion ASC""", (TID,))
gl = cur.fetchall()
if not gl:
    print("   *** goleadores_cache VACIA (sin API key o sin datos). Cargar el goleador C manual. ***")
    top_nombre = None
else:
    top_goles = gl[0]['goles']
    top = [g for g in gl if g['goles'] == top_goles]
    print(f"   Top ({top_goles} goles): {[g['nombre'] for g in top]}")
    top_nombre = top[0]['nombre']
    if len(top) > 1:
        print(f"   >>> EMPATE de goleador: {len(top)} jugadores. Se asigna '{top_nombre}'.")
        print("       (torneo.resultado_goleador es un solo campo; ajustar manual si corresponde.)")
    # match con predicciones
    cur.execute("""SELECT COUNT(*) AS n FROM apuesta_global
                   WHERE torneo_id=%s AND LOWER(TRIM(pred_goleador))=LOWER(TRIM(%s))""",
                (TID, top_nombre))
    n_match = cur.fetchone()['n']
    cur.execute("UPDATE torneo SET resultado_goleador=%s WHERE id=%s", (top_nombre, TID))
    print(f"   torneo.resultado_goleador = '{top_nombre}'  (apostadores con match exacto: {n_match})")
    if n_match == 0:
        print("   >>> Nadie coincide EXACTO con ese nombre. El engine C compara exacto (case-insensitive).")
        print("       Si tus apostadores escribieron el nombre distinto, ajusta resultado_goleador.")

# 3) Forzar puntajes final/3P + globales
print("\n== 3) POST /calcular-puntajes/2?force_grupos=true ==")
cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TID}", headers=hdr,
                   params={"force_grupos": "true"}, timeout=600)
cd = cr.json()
if not cd.get("ok"): sys.exit(f"calcular-puntajes no OK -> {cd}")
print(f"   OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  globales_procesadas={cd.get('globales_procesadas')}")
for fase, d in (cd.get("por_fase") or {}).items():
    print(f"      [{fase:<14}] total={d.get('total',0):>6} apuestas={d.get('apuestas',0):>4}")

# 4) Marcar torneo cerrado (para el banner del live)
print("\n== 4) Marcar torneo cerrado ==")
try:
    cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado BOOLEAN DEFAULT FALSE")
    cur.execute("ALTER TABLE torneo ADD COLUMN IF NOT EXISTS cerrado_at TIMESTAMPTZ")
    cur.execute("UPDATE torneo SET cerrado=TRUE, cerrado_at=NOW() WHERE id=%s", (TID,))
    print("   torneo.cerrado = TRUE")
except Exception as e:
    print(f"   (no se pudo marcar cerrado: {e})")

# 5) Ranking final + globales
print("\n== 5) RANKING FINAL (top 15) ==")
rr = requests.get(f"{API_BASE}/bets/ranking/{TID}", headers=hdr, timeout=30)
_rj = rr.json(); rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
for i, ap in enumerate(rows[:15], 1):
    nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
    print(f"   {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
          f"(part={ap.get('puntos_partidos_total',0)}, glob={ap.get('pts_globales',0)})")

# resumen globales: cuantos acertaron cada item
print("\n== Globales: apostadores con puntaje > 0 por item ==")
try:
    for col, lbl in [("pts_campeon","A campeon"),("pts_finalistas","B finalistas"),
                     ("pts_goleador","C goleador"),("pts_peor_equipo","D peor equipo"),
                     ("pts_mayor_goleada","E mayor goleada"),
                     ("pts_etapa_paraguay","F etapa PY"),("pts_goles_paraguay","G goles PY")]:
        try:
            cur.execute(f"SELECT COUNT(*) AS n FROM puntaje_global WHERE torneo_id=%s AND COALESCE({col},0)>0", (TID,))
            print(f"   {lbl:<16}: {cur.fetchone()['n']}")
        except Exception:
            pass
except Exception as e:
    print(f"   (no se pudo leer puntaje_global: {e})")

conn.close()
print("\n=== TORNEO CERRADO Y PUNTAJES FINALES CALCULADOS ===")
