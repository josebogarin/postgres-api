"""
sync_francia_iraq.py
Sincroniza el partido Francia vs Iraq desde API-Football + corrección ESPN.
Requiere servidor uvicorn corriendo en puerto 8000.
"""

import json, urllib.request, urllib.error, psycopg2, psycopg2.extras, sys
from datetime import datetime

BASE   = "http://localhost:8000/api/v1"
DB     = dict(host="localhost", port=5432, user="app_user",
              password="superpassword", dbname="becbuc")
TORNEO = 2

def log(msg):
    print(msg)

def api(method, path, data=None, tok=None):
    body = json.dumps(data).encode() if data is not None else b""
    hdrs = {"Content-Type": "application/json"}
    if tok: hdrs["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()[:300]}")

def main():
    log(f"=== sync_francia_iraq.py === {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")

    # 1. Login
    log("1. Autenticando...")
    try:
        tok = api("POST", "/auth/login", {"username": "jose", "password": "catalina"})["access_token"]
        log("   OK")
    except Exception as e:
        log(f"   ERROR login: {e}")
        log("   Verificar que uvicorn este corriendo: cd backend && .venv\\Scripts\\uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 2. Buscar partido_id de Francia vs Iraq en BD
    log("")
    log("2. Buscando partido Francia vs Iraq en BD...")
    conn = psycopg2.connect(**DB)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.id, p.estado, p.api_fixture_id,
               el.nombre AS local, ev.nombre AS visitante,
               p.goles_local, p.goles_visitante
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = %s
          AND (el.nombre ILIKE '%%franc%%' OR el.nombre ILIKE '%%irak%%' OR el.nombre ILIKE '%%iraq%%'
            OR ev.nombre ILIKE '%%franc%%' OR ev.nombre ILIKE '%%irak%%' OR ev.nombre ILIKE '%%iraq%%')
        ORDER BY p.fecha
    """, (TORNEO,))
    partidos = cur.fetchall()
    conn.close()

    if not partidos:
        log("   ERROR: no se encontro el partido en BD")
        sys.exit(1)

    for p in partidos:
        log(f"   ID={p['id']}  {p['local']} vs {p['visitante']}  "
            f"estado={p['estado']}  marcador={p['goles_local']}-{p['goles_visitante']}  "
            f"api_fixture_id={p['api_fixture_id']}")

    partido_id = partidos[0]["id"]
    api_fixture_id = partidos[0]["api_fixture_id"]

    if not api_fixture_id:
        log("   AVISO: api_fixture_id es NULL — el sync de API-Football no podra actualizar este partido.")
        log("   Verifica que el partido tenga api_fixture_id mapeado en la BD.")

    # 3. Sync general desde API-Football (actualiza todos los partidos finalizados)
    log("")
    log("3. Sincronizando desde API-Football...")
    try:
        r = api("POST", f"/bets/sync-resultados/{TORNEO}?force=true&max_detalle=20", tok=tok)
        log(f"   actualizados     : {r.get('actualizados', '?')}")
        log(f"   bracket_ok       : {r.get('bracket_ok', '?')}")
        log(f"   puntajes_ok      : {r.get('puntajes_ok', '?')}")
        if r.get("error"):
            log(f"   AVISO: {r['error']}")
    except Exception as e:
        log(f"   ERROR sync: {e}")

    # 4. Verificación ESPN para el partido específico
    log("")
    log(f"4. Verificacion ESPN para partido ID={partido_id}...")
    try:
        r = api("GET", f"/bets/espn-verify/{partido_id}", tok=tok)
        log(f"   ok               : {r.get('ok', '?')}")
        log(f"   estado           : {r.get('estado', '?')}")
        correcciones = r.get("correcciones", {})
        if correcciones:
            log(f"   Correcciones ESPN:")
            for campo, val in correcciones.items():
                log(f"     {campo}: {val}")
        else:
            log("   Sin correcciones ESPN (datos ya coinciden)")
    except Exception as e:
        log(f"   ERROR ESPN verify: {e}")

    # 5. Estado final del partido
    log("")
    log("5. Estado final del partido en BD...")
    conn = psycopg2.connect(**DB)
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.estado, p.goles_local, p.goles_visitante, p.amarillas,
               p.rojas, p.decisiones_var, p.minuto_primer_gol, p.penales_partido,
               el.nombre AS local, ev.nombre AS visitante
        FROM partido p
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.id = %s
    """, (partido_id,))
    final = cur.fetchone()
    conn.close()

    if final:
        log(f"   {final['local']} {final['goles_local']} - {final['goles_visitante']} {final['visitante']}")
        log(f"   estado     : {final['estado']}")
        log(f"   amarillas  : {final['amarillas']}")
        log(f"   rojas      : {final['rojas']}")
        log(f"   VAR        : {final['decisiones_var']}")
        log(f"   min. gol   : {final['minuto_primer_gol']}")
        log(f"   pen.partido: {final['penales_partido']}")

    log("")
    log("=== SYNC COMPLETADO ===")

if __name__ == "__main__":
    main()
