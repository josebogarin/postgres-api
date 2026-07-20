"""
Diagnóstico VAR - Francia
Busca el partido de Francia, obtiene el fixture de API-Football y muestra
todos los eventos crudos para entender cómo se reporta el VAR.
También muestra los últimos registros de api_sync_log para ese fixture.

Ejecutar:
  cd "C:\proyecto FAST API\backend"
  .venv\Scripts\Activate.ps1
  cd ..
  python diag_var_france.py [fixture_id_opcional]
"""
import psycopg2, httpx, json, sys

DB  = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
KEY = "f13bee776659e2c20c715a81ecff2307"
HEADERS = {
    "x-rapidapi-key":  KEY,
    "x-rapidapi-host": "v3.football.api-sports.io",
}
BASE = "https://v3.football.api-sports.io"

def get(path, params=None):
    url = BASE + path
    r = httpx.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def main():
    conn = psycopg2.connect(**DB)
    cur  = conn.cursor()

    # Buscar partidos de Francia con api_fixture_id
    cur.execute("""
        SELECT p.id, p.api_fixture_id,
               COALESCE(el.nombre, el.nombre_es),
               p.goles_local, p.goles_visitante,
               COALESCE(ev.nombre, ev.nombre_es),
               p.estado, p.amarillas, p.rojas, p.decisiones_var, p.fecha
        FROM partido p
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2
          AND p.api_fixture_id IS NOT NULL
          AND (el.nombre ILIKE '%france%' OR ev.nombre ILIKE '%france%'
               OR el.nombre_es ILIKE '%franc%' OR ev.nombre_es ILIKE '%franc%')
        ORDER BY p.fecha DESC LIMIT 5
    """)
    rows = cur.fetchall()

    if not rows:
        # Si no hay match por nombre, buscar todos con api_fixture_id
        print("No se encontró partido de Francia con api_fixture_id.")
        print("Listando todos los partidos con fixture ID para elegir:")
        cur.execute("""
            SELECT p.id, p.api_fixture_id,
                   COALESCE(el.nombre, el.nombre_es),
                   p.goles_local, p.goles_visitante,
                   COALESCE(ev.nombre, ev.nombre_es),
                   p.estado, p.decisiones_var, p.fecha
            FROM partido p
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2 AND p.api_fixture_id IS NOT NULL
            ORDER BY p.fecha DESC LIMIT 20
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"  partido_id={r[0]:4d}  fixture={r[1]:8d}  {str(r[2]):20s} {r[3]}-{r[4]}  {str(r[5]):20s}  {r[6]:12s}  var={r[7]}  fecha={str(r[8])[:10]}")
        cur.close(); conn.close()
        return

    print(f"Partidos de Francia encontrados en BD ({len(rows)}):")
    for r in rows:
        print(f"  partido_id={r[0]:4d}  fixture={r[1]:8d}  {str(r[2]):20s} {r[3]}-{r[4]}  {str(r[5]):20s}  estado={r[6]:12s}  amar={r[7]}  rojas={r[8]}  var={r[9]}  fecha={str(r[10])[:10]}")

    # Usar el primero (más reciente)
    pid, fix_id = rows[0][0], rows[0][1]
    print(f"\n=== Consultando API-Football fixture_id={fix_id} ===")

    data = get("/fixtures", {"id": fix_id})
    resp = data.get("response", [])
    if not resp:
        print("API devolvió 0 fixtures para ese ID.")
        print("Response completa:", json.dumps(data, indent=2)[:2000])
        cur.close(); conn.close()
        return

    fix = resp[0]
    status = fix["fixture"]["status"]
    print(f"Estado API: {status['long']} ({status['short']})")
    print(f"Goles: {fix['goals']['home']}-{fix['goals']['away']}")

    events = fix.get("events", [])
    print(f"\nEventos totales: {len(events)}")
    print("─" * 80)

    var_count = 0
    for ev in events:
        t    = ev.get("type", "")
        det  = ev.get("detail", "")
        min_ = ev.get("time", {}).get("elapsed", "?")
        ext  = ev.get("time", {}).get("extra", "")
        team = ev.get("team", {}).get("name", "?")
        player = ev.get("player", {}).get("name", "?")
        comments = ev.get("comments", "")
        marker = " ◄◄◄ VAR" if t == "Var" else ""
        ext_str = f"+{ext}" if ext else ""
        print(f"  min={min_}{ext_str:4s}  type={t:12s}  detail={det:30s}  team={team:15s}  player={player}{marker}")
        if comments:
            print(f"          comments: {comments}")
        if t == "Var":
            var_count += 1

    print(f"\n=== VAR events encontrados: {var_count} ===")

    # También mostrar statistics para amarillas/rojas
    stats = fix.get("statistics", [])
    print(f"\nStatistics ({len(stats)} teams):")
    for st in stats:
        tname = st.get("team", {}).get("name", "?")
        for s in st.get("statistics", []):
            stype = s.get("type", "")
            if stype in ("Yellow Cards", "Red Cards", "VAR", "Fouls"):
                print(f"  {tname:20s}  {stype:20s}  {s.get('value')}")

    # Guardar la respuesta completa para revisión
    out = "diag_var_france_response.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fix, f, ensure_ascii=False, indent=2)
    print(f"\nRespuesta completa guardada en: {out}")

    check_sync_log(cur, fix_id)
    cur.close()
    conn.close()

def check_sync_log(cur, fix_id):
    """Muestra últimas entradas del api_sync_log para este fixture."""
    try:
        cur.execute("""
            SELECT created_at, endpoint, status_code, response_ms,
                   LEFT(respuesta_raw::text, 300) AS resp_preview
            FROM api_sync_log
            WHERE endpoint ILIKE %s
            ORDER BY created_at DESC LIMIT 5
        """, (f"%{fix_id}%",))
        rows = cur.fetchall()
        if rows:
            print(f"\n=== Últimos {len(rows)} sync_log para fixture {fix_id} ===")
            for r in rows:
                print(f"  {str(r[0])[:19]}  status={r[2]}  ms={r[3]}")
                if r[4]:
                    print(f"    preview: {r[4][:200]}")
        else:
            print(f"\nNo hay entradas en api_sync_log para fixture {fix_id}")
    except Exception as e:
        print(f"\n(api_sync_log no disponible: {e})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Usar fixture_id pasado por argumento
        try:
            override_fix = int(sys.argv[1])
            print(f"Usando fixture_id={override_fix} pasado por argumento")
            KEY2 = "f13bee776659e2c20c715a81ecff2307"
            H2 = {"x-rapidapi-key": KEY2, "x-rapidapi-host": "v3.football.api-sports.io"}
            data = httpx.get("https://v3.football.api-sports.io/fixtures", headers=H2,
                             params={"id": override_fix}, timeout=15).json()
            resp = data.get("response", [])
            if resp:
                fix = resp[0]
                events = fix.get("events", [])
                print(f"Goles: {fix['goals']['home']}-{fix['goals']['away']}")
                print(f"Estado: {fix['fixture']['status']['long']}")
                print(f"Eventos ({len(events)}):")
                for ev in events:
                    t = ev.get("type",""); det = ev.get("detail","")
                    min_ = ev.get("time",{}).get("elapsed","?")
                    print(f"  min={min_:3}  type={t:12s}  detail={det}")
            else:
                print("Sin respuesta de API")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
    main()
