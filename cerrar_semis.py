# -*- coding: utf-8 -*-
"""
cerrar_semis.py  (sesion Cowork 2026-07-18)

Cierra la fase de SEMIFINAL de forma segura:
  0) VERIFICA que P101-P102 esten los 2 finalizados y con items API cargados.
     Si algo falta -> ABORTA (no calcula ni bloquea, para no congelar datos incompletos).
  1) POST /calcular-puntajes/2  (recalcula con semis aun ABIERTA).
  2) Bloquea la fase de SEMIS (fase.bloqueada=TRUE).
  NO toca la Final ni el 3er puesto.

Requisito previo: apuestas de semifinal YA importadas (importar_semis_excel.py --import).

Uso:
  Doble clic en run_cerrar_semis.bat
  o: backend\.venv\Scripts\python.exe cerrar_semis.py
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

API_BASE  = "http://localhost:8000/api/v1"
API_USER  = "jose"
API_PASS  = "catalina"
TORNEO_ID = 2
CONN_BEC  = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
SEMIS     = (101, 102)

print("=" * 62)
print("BECBUC - Cerrar SEMIFINAL (verificar -> calcular -> bloquear)")
print("=" * 62)

# -- Conectar BD ----------------------------------------------------
try:
    conn = psycopg2.connect(CONN_BEC)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
except Exception as e:
    sys.exit(f"ERROR conexion BD (Docker core-postgres corriendo?): {e}")

# -- 0a. Verificar que existan apuestas de semis --------------------
cur.execute("""
    SELECT COUNT(*) AS n, COUNT(DISTINCT a.apostador_id) AS aps
    FROM apuesta a JOIN partido p ON p.id=a.partido_id
    WHERE p.torneo_id=%s AND p.numero_fifa = ANY(%s)
""", (TORNEO_ID, list(SEMIS)))
ab = cur.fetchone()
print(f"\n== 0) Apuestas de semifinal en BD: {ab['n']} ({ab['aps']} apostadores) ==")
if ab['n'] == 0:
    conn.close()
    sys.exit("ABORTADO: no hay apuestas de semifinal cargadas. Correr importar_semis_excel.py --import primero.")

# -- 0b. Estado + items API de P101-P102 ----------------------------
cur.execute("""
    SELECT p.numero_fifa,
           el.nombre AS local, p.goles_local,
           p.goles_visitante, ev.nombre AS visitante,
           p.estado,
           COALESCE(p.datos_confirmados, FALSE) AS blindado,
           COALESCE(ec.nombre, 'sin definir')  AS clasificado,
           p.amarillas, p.rojas, p.decisiones_var,
           p.minuto_primer_gol, p.penales_partido,
           p.penales_local, p.penales_visitante,
           p.equipo_clasificado_id
    FROM partido p
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
    WHERE p.torneo_id = %s AND p.numero_fifa = ANY(%s)
    ORDER BY p.numero_fifa
""", (TORNEO_ID, list(SEMIS)))
partidos = cur.fetchall()

if not partidos:
    conn.close()
    sys.exit("ERROR: no se encontraron los partidos P101-P102. Revisar numero_fifa/torneo.")

def _v(x):
    return "NULL" if x is None else str(x)

pendientes, sin_blindar, items_incompletos = [], [], []

for p in partidos:
    fin  = p['estado'] == 'finalizado'
    marca = "OK " if fin else "!! "
    hubo_goles = (p['goles_local'] or 0) + (p['goles_visitante'] or 0) > 0
    empate = p['goles_local'] == p['goles_visitante']
    faltan = []
    if p['amarillas']       is None: faltan.append('amarillas')
    if p['rojas']           is None: faltan.append('rojas')
    if p['decisiones_var']  is None: faltan.append('VAR')
    if p['penales_partido'] is None: faltan.append('penales_partido(M)')
    if hubo_goles and p['minuto_primer_gol'] is None: faltan.append('minuto_gol(N)')
    if empate and (p['penales_local'] is None or p['penales_visitante'] is None):
        faltan.append('tanda(O)')
    if p['equipo_clasificado_id'] is None: faltan.append('clasificado(P)')

    print(f"  {marca}P{p['numero_fifa']:03d}: {p['local']:<22} {p['goles_local']}-"
          f"{p['goles_visitante']} {p['visitante']:<22} | {p['estado']:<11}"
          f" | blindado={'SI' if p['blindado'] else 'no'} | Clasifica: {p['clasificado']}")
    print(f"        items: J.amar={_v(p['amarillas'])}  K.rojas={_v(p['rojas'])}"
          f"  L.VAR={_v(p['decisiones_var'])}  M.penJuego={_v(p['penales_partido'])}"
          f"  N.min={_v(p['minuto_primer_gol'])}"
          f"  O.tanda={_v(p['penales_local'])}-{_v(p['penales_visitante'])}")
    if faltan:
        print(f"        ! items faltantes (NULL): {', '.join(faltan)}")

    if not fin:
        pendientes.append(p['numero_fifa'])
    else:
        if not p['blindado']:
            sin_blindar.append(p['numero_fifa'])
        if faltan:
            items_incompletos.append((p['numero_fifa'], faltan))

# -- Guardas de seguridad -------------------------------------------
if pendientes:
    conn.close()
    print("\n" + "!" * 62)
    print(f"ABORTADO: semis NO finalizados: {['P%03d' % n for n in pendientes]}")
    print("No se calcularon puntajes ni se bloqueo la fase.")
    print("Si ya se jugaron: POST /sync-resultados/2?force=true y volver a correr.")
    print("!" * 62)
    sys.exit(1)

if items_incompletos:
    conn.close()
    print("\n" + "!" * 62)
    print("ABORTADO: partidos finalizados pero con items de la API sin cargar (NULL):")
    for n, faltan in items_incompletos:
        print(f"   P{n:03d}: {', '.join(faltan)}")
    print("Estos items alimentan el scoring (J/K/L/M/N/O/P). Cerrar ahora congelaria")
    print("puntajes incompletos. Solucion: POST /sync-resultados/2?force=true y reintentar.")
    print("!" * 62)
    sys.exit(1)

print("\n  -> Los 2 semis estan finalizados y con todos los items cargados.")
if sin_blindar:
    print(f"  NOTA: no blindados (datos_confirmados=FALSE): {['P%03d' % n for n in sin_blindar]}")
    print("        El cierre igual procede; blindar es un paso admin aparte (opcional).")

# -- 1. Calcular puntajes (semis aun ABIERTA) -----------------------
print("\n== 1) Calculando puntajes (POST /calcular-puntajes/2) ==")
try:
    lr = requests.post(f"{API_BASE}/auth/login",
                       json={"username": API_USER, "password": API_PASS}, timeout=30)
    tok = lr.json().get("access_token", "")
except Exception as e:
    conn.close(); sys.exit(f"ERROR login (uvicorn corriendo en :8000?): {e}")
if not tok:
    conn.close(); sys.exit(f"ERROR: login sin token -> {lr.status_code} {lr.text[:200]}")

hdr = {"Authorization": f"Bearer {tok}"}
try:
    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}", headers=hdr, timeout=300)
    cd = cr.json()
except Exception as e:
    conn.close(); sys.exit(f"ERROR recalculo: {e}")

if cd.get("ok"):
    print(f"  OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  fallos={cd.get('fallos')}")
    for fase, d in (cd.get("por_fase") or {}).items():
        print(f"    [{fase}] marcador={d.get('marcador',0)} bonus={d.get('bonus',0)}"
              f" total={d.get('total',0)} apuestas={d.get('apuestas',0)}")
    print(f"  globales_procesadas={cd.get('globales_procesadas')}")
else:
    conn.close(); sys.exit(f"ERROR: calcular-puntajes no OK -> {cd}")

# -- 2. Bloquear fase de semis --------------------------------------
print("\n== 2) Bloqueando fase de SEMIS ==")
cur.execute("""
    SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
    FROM fase
    WHERE torneo_id = %s
      AND (tipo ILIKE 'semis' OR tipo ILIKE '%%semi%%' OR nombre ILIKE '%%semi%%')
    ORDER BY id
""", (TORNEO_ID,))
fases = cur.fetchall()
if not fases:
    print("  ! No se encontro fase de semis. Fases del torneo:")
    cur.execute("SELECT id, nombre, tipo FROM fase WHERE torneo_id=%s ORDER BY id", (TORNEO_ID,))
    for f in cur.fetchall():
        print(f"    id={f['id']} tipo='{f['tipo']}' nombre='{f['nombre']}'")
else:
    for f in fases:
        if f['bloqueada']:
            print(f"  = id={f['id']} [{f['tipo']}] {f['nombre']} -> ya estaba BLOQUEADA")
        else:
            cur.execute("UPDATE fase SET bloqueada=TRUE WHERE id=%s", (f['id'],))
            print(f"  OK id={f['id']} [{f['tipo']}] {f['nombre']} -> BLOQUEADA ahora")

# -- 3. Ranking top-10 ----------------------------------------------
print("\n== 3) Top 10 Ranking ==")
try:
    rr = requests.get(f"{API_BASE}/bets/ranking/{TORNEO_ID}", headers=hdr, timeout=30)
    _rj = rr.json()
    _rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
    for i, ap in enumerate(_rows[:10], 1):
        nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
        print(f"  {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
              f"(partidos={ap.get('puntos_partidos_total',0)}, globales={ap.get('pts_globales',0)})")
except Exception as e:
    print(f"  Error ranking: {e}")

conn.close()
print("\nSemis cerradas. Falta cargar/abrir Final (P104) y 3er puesto (P103).")
