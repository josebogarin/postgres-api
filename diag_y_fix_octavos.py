"""
Diagnóstico y fix para octavos (ronda16):
1. Muestra estado BD de R16
2. Muestra últimas líneas de sync_auto.log
3. Llama /api-mapeo/2/auto para mapear api_fixture_id
4. Llama /sync-partido/{num} para cada R16 finalizado
5. Llama /calcular-puntajes/2
"""
import subprocess, sys, os, json, time

BASE_URL = "http://localhost:8000"
USER = "jose"
PASS = "catalina"

# ─── helpers ───────────────────────────────────────────────────────────────

def docker_query(sql):
    result = subprocess.run(
        ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", "becbuc",
         "-c", sql],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout if result.returncode == 0 else f"ERROR: {result.stderr}"

def api(method, path, **kwargs):
    import urllib.request, urllib.error
    url = BASE_URL + path
    data = json.dumps(kwargs.get("body", None)).encode() if "body" in kwargs else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Content-Type", "application/json")
    if "token" in kwargs:
        req.add_header("Authorization", f"Bearer {kwargs['token']}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:300]}")
        return None
    except Exception as ex:
        print(f"  Error: {ex}")
        return None

def login():
    r = api("POST", "/api/v1/auth/login", body={"username": USER, "password": PASS})
    if r and "access_token" in r:
        print(f"  ✅ Login OK (jose)")
        return r["access_token"]
    print(f"  ❌ Login falló: {r}")
    return None

# ─── paso 1: BD ───────────────────────────────────────────────────────────

print("\n" + "="*60)
print("PASO 1: Estado R16 en base de datos")
print("="*60)

sql = """
SELECT
    p.numero_fifa AS num,
    el.nombre AS local,
    p.goles_local AS gl,
    p.goles_visitante AS gv,
    ev.nombre AS visitante,
    p.penales_local AS pen_l,
    p.penales_visitante AS pen_v,
    p.amarillas, p.rojas, p.decisiones_var AS var,
    p.penales_partido AS pen_part,
    p.minuto_primer_gol AS min_gol,
    p.estado,
    COALESCE(f.bloqueada, FALSE) AS fase_bloq,
    p.api_fixture_id,
    p.datos_confirmados AS confirmado
FROM partido p
JOIN fase f ON f.id = p.fase_id
LEFT JOIN equipo el ON el.id = p.equipo_local_id
LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE f.tipo = 'ronda16'
ORDER BY p.numero_fifa;
"""
print(docker_query(sql))

# ─── paso 2: sync_auto.log ───────────────────────────────────────────────

print("\n" + "="*60)
print("PASO 2: Últimas líneas de sync_auto.log")
print("="*60)

log_path = r"C:\proyecto FAST API\sync_auto.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"Total líneas en log: {len(lines)}")
    print("Últimas 30 líneas:")
    print("".join(lines[-30:]))
except FileNotFoundError:
    print(f"  ⚠ No encontrado: {log_path}")
except Exception as e:
    print(f"  Error leyendo log: {e}")

# ─── paso 3: login ───────────────────────────────────────────────────────

print("\n" + "="*60)
print("PASO 3: Login en API")
print("="*60)

token = login()
if not token:
    print("No se pudo continuar sin token.")
    input("\nPresioná Enter para cerrar...")
    sys.exit(1)

# ─── paso 4: auto-mapeo ──────────────────────────────────────────────────

print("\n" + "="*60)
print("PASO 4: Auto-mapeo api_fixture_id (R16)")
print("="*60)

r = api("POST", "/api/v1/bets/api-mapeo/2/auto", token=token)
print(f"  Resultado mapeo: {r}")

# ─── paso 5: consultar y sync cada R16 ───────────────────────────────────

print("\n" + "="*60)
print("PASO 5: Consulta y sync de cada partido R16")
print("="*60)

# R16 son P89-P96
for num in range(89, 97):
    print(f"\n--- P{num} ---")
    consulta = api("GET", f"/api/v1/bets/consulta-partido/{num}", token=token)
    if consulta:
        bd = consulta.get("bd", {})
        ap = consulta.get("api", {})
        diffs = consulta.get("diferencias", {})
        print(f"  BD: {bd.get('local','?')} {bd.get('goles_local','?')}-{bd.get('goles_visitante','?')} {bd.get('visitante','?')} | estado={bd.get('estado','?')} | api_fixture_id={bd.get('api_fixture_id','NULL')}")
        if ap:
            print(f"  API: goles {ap.get('goles_local','?')}-{ap.get('goles_visitante','?')} | estado_api={ap.get('estado_api','?')}")
        if diffs:
            print(f"  ⚠ Diferencias: {diffs}")

        # Si tiene api_fixture_id y está finalizado o hay diferencias, syncear
        if bd.get("api_fixture_id") and (bd.get("estado") == "finalizado" or diffs):
            print(f"  → Sincronizando P{num}...")
            sync_r = api("POST", f"/api/v1/bets/sync-partido/{num}", token=token)
            if sync_r:
                print(f"     goles={sync_r.get('goles')}, bracket_ok={sync_r.get('bracket_ok')}, puntajes_ok={sync_r.get('puntajes_ok')}")
        elif not bd.get("api_fixture_id"):
            print(f"  ⚠ Sin api_fixture_id — el mapeo no encontró este partido en API-Football")
    else:
        print(f"  ⚠ No se pudo consultar P{num} (no existe o sin api_fixture_id)")

# ─── paso 6: calcular puntajes ───────────────────────────────────────────

print("\n" + "="*60)
print("PASO 6: Calcular puntajes torneo 2")
print("="*60)

r = api("POST", "/api/v1/bets/calcular-puntajes/2", token=token)
if r:
    print(f"  plenos={r.get('plenos')}, aciertos={r.get('aciertos')}, fallos={r.get('fallos')}")
    print(f"  por_fase={r.get('por_fase', {})}")
    print(f"  globales={r.get('globales_procesadas')}")
else:
    print("  ❌ Error al calcular puntajes")

# ─── resumen ────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("RESUMEN FINAL: Estado R16 post-fix")
print("="*60)
print(docker_query(sql))

print("\n✅ Script completado.")
input("\nPresioná Enter para cerrar...")
