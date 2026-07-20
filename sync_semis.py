# -*- coding: utf-8 -*-
"""
sync_semis.py
Opcion A: sincroniza desde API-Football (POST /sync-resultados/2?force=true).
  - auto-mapea api_fixture_id de partidos con equipos definidos (P102, etc.)
  - trae resultados de partidos ya jugados (P101/P102 si finalizaron en la API)
  - avanza el bracket -> propaga ganadores a Final (P104) y 3er puesto (P103)
NO bloquea ninguna fase. (El sync dispara calcular-puntajes, pero como las semis
no tienen apuestas cargadas, no genera puntajes de semis.)
Luego re-muestra el estado de P101-P104.
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
API_USER, API_PASS = "jose", "catalina"
TORNEO_ID = 2
CONN_BEC  = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

print("=" * 66)
print("BECBUC - Sync API-Football + avanzar bracket (Semis)")
print("=" * 66)

# ── login ──────────────────────────────────────────────────────
try:
    lr = requests.post(f"{API_BASE}/auth/login",
                       json={"username": API_USER, "password": API_PASS}, timeout=30)
    tok = lr.json().get("access_token", "")
except Exception as e:
    sys.exit(f"ERROR login (uvicorn corriendo en :8000?): {e}")
if not tok:
    sys.exit(f"ERROR: login sin token -> {lr.status_code} {lr.text[:200]}")
hdr = {"Authorization": f"Bearer {tok}"}

# ── sync-resultados force ──────────────────────────────────────
print("\n== 1) POST /sync-resultados/2?force=true ==")
try:
    sr = requests.post(f"{API_BASE}/bets/sync-resultados/{TORNEO_ID}?force=true",
                       headers=hdr, timeout=300)
    sd = sr.json()
except Exception as e:
    sys.exit(f"ERROR sync: {e}")

if isinstance(sd, dict):
    print(f"  ok={sd.get('ok')}  actualizados={sd.get('actualizados')}"
          f"  bracket_ok={sd.get('bracket_ok')}  puntajes_ok={sd.get('puntajes_ok')}")
    if sd.get("auto_mapeo"):
        print(f"  auto_mapeo={sd.get('auto_mapeo')}")
    if sd.get("error"):
        print(f"  ⚠ error={sd.get('error')}")
else:
    print(f"  RESPUESTA: {sd}")

# ── re-mostrar estado P101-P104 ────────────────────────────────
print("\n== 2) Estado P101-P104 tras el sync ==")
conn = psycopg2.connect(CONN_BEC)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT p.numero_fifa,
           el.nombre AS local, p.goles_local,
           p.goles_visitante, ev.nombre AS visitante,
           p.estado, p.api_fixture_id,
           COALESCE(ec.nombre, 'sin definir') AS clasificado,
           p.penales_local, p.penales_visitante
    FROM partido p
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
    WHERE p.torneo_id=%s AND p.numero_fifa = ANY(%s)
    ORDER BY p.numero_fifa
""", (TORNEO_ID, [101, 102, 103, 104]))
for p in cur.fetchall():
    fx = p['api_fixture_id'] if p['api_fixture_id'] is not None else 'sin mapear'
    tanda = ""
    if p['penales_local'] is not None or p['penales_visitante'] is not None:
        tanda = f" (tanda {p['penales_local']}-{p['penales_visitante']})"
    print(f"  P{p['numero_fifa']:03d}: {p['local']:<22} {p['goles_local']}-{p['goles_visitante']} "
          f"{p['visitante']:<22}{tanda}")
    print(f"        estado={p['estado']:<12} api_fixture={fx:<12} Clasifica: {p['clasificado']}")
conn.close()
print("\nListo. (fases NO bloqueadas; puntajes de semis no se generan sin apuestas)")
