"""
Flujo correcto:
1. Blindar todos los partidos finalizados (datos_confirmados=TRUE) via API
   → Esto impide que sync_auto los sobreescriba
2. Aplicar correcciones del Excel consolidado via psql (sin restriccion datos_confirmados)
3. Recalcular puntajes via API

El sync_auto respeta datos_confirmados=TRUE y no los toca.
"""
import subprocess, json, urllib.request, urllib.error, sys
from datetime import datetime

BASE = "http://localhost:8000"
TORNEO_ID = 2

def log(msg=""):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def api(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read()), e.code
        except:
            return {"error": str(e)}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

def psql(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

# ============================================================
# DATOS DEL EXCEL (hoja "40- RESULTADOS OFICIALES")
# ============================================================
EXCEL_DATA = {
    1: {"amarillas": 3, "rojas": 3, "var": 1, "penales_partido": 0, "minuto_primer_gol": 9},
    2: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 59},
    3: {"amarillas": 5, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 21},
    4: {"amarillas": 6, "rojas": 0, "var": 2, "penales_partido": 0, "minuto_primer_gol": 7},
    5: {"amarillas": 4, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 28},
    6: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 27},
    7: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 21},
    8: {"amarillas": 3, "rojas": 0, "var": 1, "penales_partido": 1, "minuto_primer_gol": 17},
    9: {"amarillas": 4, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 90},
    10: {"amarillas": 0, "rojas": 0, "var": 0, "penales_partido": 1, "minuto_primer_gol": 6},
    11: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 51},
    12: {"amarillas": 1, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 7},
    13: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 41},
    14: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 99},
    15: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 7},
    16: {"amarillas": 4, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 20},
    17: {"amarillas": 0, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 66},
    18: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 29},
    19: {"amarillas": 0, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 17},
    20: {"amarillas": 1, "rojas": 0, "var": 2, "penales_partido": 1, "minuto_primer_gol": 21},
    21: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 95},
    22: {"amarillas": 0, "rojas": 0, "var": 1, "penales_partido": 1, "minuto_primer_gol": 12},
    23: {"amarillas": 4, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 6},
    24: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 40},
    25: {"amarillas": 3, "rojas": 0, "var": 1, "penales_partido": 1, "minuto_primer_gol": 6},
    26: {"amarillas": 3, "rojas": 1, "var": 1, "penales_partido": 1, "minuto_primer_gol": 74},
    27: {"amarillas": 2, "rojas": 2, "var": 3, "penales_partido": 0, "minuto_primer_gol": 16},
    28: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 50},
    29: {"amarillas": 4, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 23},
    30: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 2},
    31: {"amarillas": 2, "rojas": 1, "var": 0, "penales_partido": 0, "minuto_primer_gol": 2},
    32: {"amarillas": 7, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 11},
    33: {"amarillas": 0, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 30},
    34: {"amarillas": 6, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 99},
    35: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 5},
    36: {"amarillas": 0, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 4},
    37: {"amarillas": 4, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 21},
    38: {"amarillas": 2, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 10},
    39: {"amarillas": 2, "rojas": 1, "var": 2, "penales_partido": 0, "minuto_primer_gol": 99},
    40: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 15},
    41: {"amarillas": 0, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 43},
    42: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 14},
    43: {"amarillas": 4, "rojas": 0, "var": 1, "penales_partido": 1, "minuto_primer_gol": 38},
    44: {"amarillas": 2, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 36},
    45: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 99},
    46: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 54},
    47: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 6},
    48: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 76},
    49: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 7},
    50: {"amarillas": 3, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 10},
    51: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 46},
    52: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 29},
    53: {"amarillas": 1, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 54},
    54: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 63},
    55: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 7},
    56: {"amarillas": 4, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 2},
    57: {"amarillas": 3, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 56},
    58: {"amarillas": 0, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 3},
    59: {"amarillas": 2, "rojas": 0, "var": 1, "penales_partido": 0, "minuto_primer_gol": 2},
    60: {"amarillas": 2, "rojas": 0, "var": 0, "penales_partido": 0, "minuto_primer_gol": 99},
}

FIELD_MAP = {
    'amarillas': 'amarillas',
    'rojas': 'rojas',
    'var': 'decisiones_var',
    'penales_partido': 'penales_partido',
    'minuto_primer_gol': 'minuto_primer_gol',
}

print("=== BLINDAR + CORREGIR EXCEL + RECALCULAR ===\n")

# 1. Login
log("[1/5] Login API...")
r, s = api("POST", "/api/v1/auth/login", {"username": "jose", "password": "catalina"})
if s != 200:
    log(f"  ERROR login: {s} {r}")
    input("Press Enter..."); sys.exit(1)
tok = r["access_token"]
log("  OK")

# 2. Blindar todos los partidos finalizados
log(f"\n[2/5] Blindando partidos finalizados (datos_confirmados=TRUE)...")
r, s = api("POST", f"/api/v1/bets/confirmar-partido-stats/{TORNEO_ID}", token=tok)
if s == 200:
    log(f"  OK - {r.get('message', r.get('confirmados', r))}")
else:
    log(f"  WARNING {s}: {r}")

# 3. Leer partidos desde BD (ahora todos confirmados)
log(f"\n[3/5] Leyendo partidos de BD...")
rows, err = psql("""
    SELECT p.id, p.numero_fifa,
           COALESCE(p.amarillas::text,'NULL'),
           COALESCE(p.rojas::text,'NULL'),
           COALESCE(p.decisiones_var::text,'NULL'),
           COALESCE(p.penales_partido::text,'NULL'),
           COALESCE(p.minuto_primer_gol::text,'NULL')
    FROM partido p
    WHERE p.torneo_id=2 AND p.estado='finalizado'
    ORDER BY p.numero_fifa ASC
""")
db_data = {}
for row in rows:
    cols = row.split("|")
    num = int(cols[1])
    db_data[num] = {
        'id': cols[0].strip(),
        'amarillas': None if cols[2]=='NULL' else int(cols[2]),
        'rojas':     None if cols[3]=='NULL' else int(cols[3]),
        'var':       None if cols[4]=='NULL' else int(cols[4]),
        'penales_partido': None if cols[5]=='NULL' else int(cols[5]),
        'minuto_primer_gol': None if cols[6]=='NULL' else int(cols[6]),
    }
log(f"  {len(db_data)} partidos finalizados en BD")

# 4. Comparar y aplicar correcciones (sin restriccion datos_confirmados)
log(f"\n[4/5] Aplicando correcciones del Excel...")
updates_ok = 0
updates_err = 0
for num in sorted(EXCEL_DATA.keys()):
    ex = EXCEL_DATA[num]
    if num not in db_data:
        continue
    db = db_data[num]
    pid = db['id']
    sets = {}
    for ex_key, db_col in FIELD_MAP.items():
        if ex[ex_key] != db[ex_key]:
            sets[db_col] = ex[ex_key]
    if sets:
        set_clause = ", ".join(f"{col}={val}" for col, val in sets.items())
        # Sin restriccion datos_confirmados - corregimos sobre registros ya blindados
        sql = f"UPDATE partido SET {set_clause} WHERE id={pid}"
        _, err2 = psql(sql)
        if err2 and 'ERROR' in err2:
            log(f"  ERROR P{num:03d}: {err2}")
            updates_err += 1
        else:
            log(f"  ✓ P{num:03d}: {set_clause}")
            updates_ok += 1

log(f"  Actualizados: {updates_ok} | Errores: {updates_err}")

# 5. Recalcular puntajes
log(f"\n[5/5] Recalculando puntajes...")
r, s = api("POST", f"/api/v1/bets/calcular-puntajes/{TORNEO_ID}", token=tok)
if s == 200:
    log(f"  OK - procesados={r.get('puntajes_procesados', r.get('procesados', '?'))}")
    log(f"       plenos={r.get('plenos','?')} aciertos={r.get('aciertos','?')}")
else:
    log(f"  WARNING {s}: {r}")

print("\n=== LISTO ===")
print("Los partidos quedan BLINDADOS (datos_confirmados=TRUE).")
print("El sync_auto NO los sobreescribirá en el futuro.")
input("\nPresioná Enter para cerrar...")
