"""
Compara TBL_CONSOLIDADA con la BD y actualiza partidos no bloqueados.
Actualiza: amarillas, rojas, decisiones_var, penales_partido, minuto_primer_gol
Solo toca partidos donde datos_confirmados=FALSE.
"""
import subprocess, json
from datetime import datetime

LOG = open("update_from_excel_log.txt", "w", encoding="utf-8")

def log(msg=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG.write(line + "\n")
    LOG.flush()

def psql(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

# Datos del Excel (extraídos de hoja "40- RESULTADOS OFICIALES", estado=FINALIZADO)
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

def main():
    log("=== UPDATE DESDE EXCEL CONSOLIDADA ===")
    log(f"Partidos en Excel: {len(EXCEL_DATA)}")

    # 1. Leer DB
    log("\n[1] Leyendo partidos finalizados desde BD...")
    rows, err = psql("""
        SELECT p.id, p.numero_fifa,
               COALESCE(p.amarillas::text,'NULL'),
               COALESCE(p.rojas::text,'NULL'),
               COALESCE(p.decisiones_var::text,'NULL'),
               COALESCE(p.penales_partido::text,'NULL'),
               COALESCE(p.minuto_primer_gol::text,'NULL'),
               p.datos_confirmados::text
        FROM partido p
        WHERE p.torneo_id=2 AND p.estado='finalizado'
        ORDER BY p.numero_fifa ASC
    """)
    if err and 'ERROR' in err:
        log(f"ERROR consultando BD: {err}")
        return

    db_data = {}
    for r in rows:
        cols = r.split("|")
        num = int(cols[1])
        db_data[num] = {
            'id': cols[0].strip(),
            'amarillas': None if cols[2]=='NULL' else int(cols[2]),
            'rojas': None if cols[3]=='NULL' else int(cols[3]),
            'var': None if cols[4]=='NULL' else int(cols[4]),
            'penales_partido': None if cols[5]=='NULL' else int(cols[5]),
            'minuto_primer_gol': None if cols[6]=='NULL' else int(cols[6]),
            'confirmado': cols[7].strip() == 't',
        }
    log(f"  Partidos finalizados en BD: {len(db_data)}")

    # 2. Comparar y encontrar diferencias
    log("\n[2] Comparando Excel vs BD...")
    FIELD_MAP = {
        'amarillas': 'amarillas',
        'rojas': 'rojas',
        'var': 'decisiones_var',
        'penales_partido': 'penales_partido',
        'minuto_primer_gol': 'minuto_primer_gol',
    }

    updates_needed = {}  # partido_id -> {campo_db: nuevo_valor}
    diffs_log = []

    for num in sorted(EXCEL_DATA.keys()):
        ex = EXCEL_DATA[num]
        if num not in db_data:
            log(f"  P{num:03d}: no está en DB como finalizado, saltando")
            continue
        db = db_data[num]
        pid = db['id']

        for ex_key, db_col in FIELD_MAP.items():
            ex_val = ex[ex_key]
            db_val = db[ex_key]
            if ex_val != db_val:
                flag = "🔒 BLOQUEADO" if db['confirmado'] else "✏️  editable"
                diffs_log.append(f"  P{num:03d} {flag} | {ex_key:<20} Excel={ex_val} BD={db_val}")
                if not db['confirmado']:
                    if pid not in updates_needed:
                        updates_needed[pid] = {'numero': num}
                    updates_needed[pid][db_col] = ex_val

    for d in diffs_log:
        log(d)

    # Count
    nums_editable = set(updates_needed.keys())
    nums_bloqueados = set(
        db_data[num]['id'] for num in EXCEL_DATA
        if num in db_data and db_data[num]['confirmado'] and
        any(EXCEL_DATA[num][k] != db_data[num][k] for k in FIELD_MAP)
    )
    log(f"\n  Partidos con diferencias a actualizar (no bloqueados): {len(nums_editable)}")
    log(f"  Partidos con diferencias bloqueados (datos_confirmados=TRUE): {len(nums_bloqueados)}")

    if not updates_needed:
        log("\n✓ No hay diferencias en partidos editables. Nada que actualizar.")
        return

    # 3. Aplicar updates
    log("\n[3] Aplicando actualizaciones...")
    ok = 0
    errors = 0
    for pid, upd in sorted(updates_needed.items(), key=lambda x: x[1].get('numero',0)):
        num = upd.pop('numero')
        # Build SET clause
        sets = []
        for col, val in upd.items():
            sets.append(f"{col}={val}")
        set_clause = ", ".join(sets)
        sql = f"UPDATE partido SET {set_clause} WHERE id={pid} AND datos_confirmados=FALSE"
        _, err = psql(sql)
        if err and 'ERROR' in err:
            log(f"  ERROR P{num:03d} (id={pid}): {err}")
            errors += 1
        else:
            log(f"  ✓ P{num:03d} (id={pid}): {set_clause}")
            ok += 1

    log(f"\n  Actualizados: {ok} | Errores: {errors}")

    # 4. Recalcular puntajes via PS1
    if ok > 0:
        log("\n[4] Generando script para recalcular puntajes...")
        ps1 = '''# Recalcular puntajes post-update excel
$base = "http://localhost:8000/api/v1"
$tok = (Invoke-RestMethod "$base/auth/login" -Method POST -ContentType "application/json" -Body '{"username":"jose","password":"catalina"}').access_token
$h = @{ Authorization = "Bearer $tok" }
Write-Host "Recalculando puntajes..." -ForegroundColor Yellow
$r = Invoke-RestMethod "$base/bets/calcular-puntajes/2" -Method POST -Headers $h -TimeoutSec 120
Write-Host "Procesados: $($r.procesados) apostadores" -ForegroundColor Green
Write-Host "Listo. Presioná Enter para cerrar."
Read-Host
'''
        with open("recalc_post_excel.ps1", "w", encoding="utf-8") as f:
            f.write(ps1)
        log("  Script guardado: recalc_post_excel.ps1")
        log("\nPRÓXIMOS PASOS:")
        log("  1. Ejecutar recalc_post_excel.ps1 para recalcular puntajes")
        log("     (doble click o clic derecho → Ejecutar con PowerShell)")

    log("\n=== COMPLETADO ===")
    LOG.close()

if __name__ == "__main__":
    main()
    input("\nPresioná Enter para cerrar...")
