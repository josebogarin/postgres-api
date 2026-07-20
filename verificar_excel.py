"""
Verifica que la BD coincide con el Excel consolidado (post-update).
Escribe resultado en verificar_excel_log.txt
"""
import subprocess
from datetime import datetime

LOG_FILE = "verificar_excel_log.txt"

def psql(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

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

lines = []
def out(msg=""):
    print(msg)
    lines.append(msg)

out(f"[{datetime.now().strftime('%H:%M:%S')}] === VERIFICACION POST-UPDATE: Excel vs BD ===\n")

rows, err = psql("""
    SELECT p.numero_fifa,
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
    out(f"ERROR BD: {err}")
else:
    db_data = {}
    for r in rows:
        cols = r.split("|")
        num = int(cols[0])
        db_data[num] = {
            'amarillas': None if cols[1]=='NULL' else int(cols[1]),
            'rojas':     None if cols[2]=='NULL' else int(cols[2]),
            'var':       None if cols[3]=='NULL' else int(cols[3]),
            'penales_partido': None if cols[4]=='NULL' else int(cols[4]),
            'minuto_primer_gol': None if cols[5]=='NULL' else int(cols[5]),
            'confirmado': cols[6].strip() == 't',
        }

    diffs = []
    ok_count = 0

    for num in sorted(EXCEL_DATA.keys()):
        ex = EXCEL_DATA[num]
        if num not in db_data:
            out(f"  P{num:03d}: NO está en BD como finalizado")
            continue
        db = db_data[num]
        partido_diffs = []
        for ex_key, db_col in FIELD_MAP.items():
            ex_val = ex[ex_key]
            db_val = db[ex_key]
            if ex_val != db_val:
                partido_diffs.append(f"{ex_key}: Excel={ex_val} BD={db_val}")
        if partido_diffs:
            lock = "BLOQUEADO" if db['confirmado'] else "editable"
            diffs.append(f"  [{lock}] P{num:03d}: {' | '.join(partido_diffs)}")
        else:
            ok_count += 1

    out(f"Partidos verificados: {len(EXCEL_DATA)}")
    out(f"  Coinciden: {ok_count}")
    out(f"  Diferencias: {len(diffs)}")

    if diffs:
        out("\nDIFERENCIAS ENCONTRADAS:")
        for d in diffs:
            out(d)
    else:
        out("\n>>> TODOS LOS 60 PARTIDOS COINCIDEN CON EL EXCEL <<<")

out("\n=== FIN ===")

with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"\nLog guardado en {LOG_FILE}")
