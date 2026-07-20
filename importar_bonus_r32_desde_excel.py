"""
importar_bonus_r32_desde_excel.py
=====================================
Lee la hoja "50- TBL MASTER" y actualiza en BD las predicciones de bonus
para todos los apostadores en R32 (P073-P088):
  pred_local, pred_visitante (goles)
  pred_amarillas, pred_rojas, pred_var, pred_penales_partido
  pred_minuto_gol
  pred_penales_local_tanda, pred_penales_visitante_tanda

Columnas en TBL MASTER:
  col[12]=pred_local, col[14]=pred_visitante
  col[24]=J-AMARILLAS, col[25]=K-ROJAS, col[26]=L-VAR, col[27]=M-PENALES
  col[28]=N-1ER GOL, col[29]=O-TANDA EQ1, col[30]=O-TANDA EQ2

Ejecutar:
  cd "C:\proyecto FAST API"
  $excel = "C:\...\20260702- TBL CHECK PARA JOSE.xlsx"
  backend\.venv\Scripts\python.exe importar_bonus_r32_desde_excel.py $excel
"""

import sys, pathlib, openpyxl, psycopg2, collections

BECBUC_DB = {"host": "localhost", "port": 5432,
             "dbname": "becbuc",  "user": "app_user", "password": "superpassword"}
APP_DB    = {"host": "localhost", "port": 5432,
             "dbname": "app_db",  "user": "app_user", "password": "superpassword"}
TORNEO_ID = 2

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else None
if not EXCEL_PATH:
    uploads = (pathlib.Path(r"C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions")
               / "a9fdc79d-9227-450c-a0c1-27eafc601471"
               / "dfc0381f-d9d1-4349-b3fa-24cab5c5da8b"
               / "local_9db4502a-7e61-4142-bb4b-38eee8035736" / "uploads")
    matches = list(uploads.glob("*TBL CHECK*.xlsx")) if uploads.exists() else []
    EXCEL_PATH = str(matches[0]) if matches else None
if not EXCEL_PATH:
    sys.exit("❌ Pasá la ruta del Excel como argumento.")

print(f"📂 {EXCEL_PATH}\n")

def iv(v, none_if=None):
    try:
        x = int(v) if v is not None else None
        if none_if is not None and x == none_if: return None
        return x
    except: return None

# ── 1. Leer predicciones del TBL MASTER ──────────────────────────────────────
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True, read_only=True)
ws = wb["50- TBL MASTER"]

# excel_preds[nf][alias] = dict de predicciones
excel_preds = collections.defaultdict(dict)

for row in ws.iter_rows(min_row=2, values_only=True):
    pid = row[1]
    if not pid or not str(pid).startswith('P'): continue
    try: nf = int(str(pid)[1:])
    except: continue
    if not (73 <= nf <= 88): continue

    alias = str(row[9]).strip().lstrip('\xa0').lstrip() if row[9] else ''
    if not alias: continue

    excel_preds[nf][alias] = {
        "pred_local":                  iv(row[12]),
        "pred_visitante":              iv(row[14]),
        "pred_amarillas":              iv(row[24]),
        "pred_rojas":                  iv(row[25]),
        "pred_var":                    iv(row[26]),
        "pred_penales_partido":        iv(row[27]),
        "pred_minuto_gol":             iv(row[28]),
        "pred_penales_local_tanda":    iv(row[29], none_if=99),
        "pred_penales_visitante_tanda": iv(row[30], none_if=99),
    }

partidos_ex = sorted(excel_preds.keys())
n_ap = len(set(a for d in excel_preds.values() for a in d))
print(f"✅ Excel: {len(partidos_ex)} partidos R32, ~{n_ap} apostadores por partido")

# ── 2. Obtener alias_map de app_db ────────────────────────────────────────────
conn_app = psycopg2.connect(**APP_DB)
cur_app  = conn_app.cursor()
cur_app.execute("""
    SELECT u.id, u.username
    FROM users u JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles ro ON ro.id = ur.role_id
    WHERE ro.name = 'apostador' AND u.is_active = TRUE
""")
# alias_map: username_lower → id
alias_map = {row[1].lower(): row[0] for row in cur_app.fetchall()}
cur_app.close(); conn_app.close()

# ── 3. Obtener partido_id por numero_fifa de becbuc ───────────────────────────
conn = psycopg2.connect(**BECBUC_DB)
cur  = conn.cursor()

cur.execute("""
    SELECT p.numero_fifa, p.id
    FROM partido p JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = %s AND p.numero_fifa BETWEEN 73 AND 88
""", (TORNEO_ID,))
partido_id_map = {nf: pid for nf, pid in cur.fetchall()}

# ── 4. Actualizar apuesta ─────────────────────────────────────────────────────
CAMPOS = ["pred_local", "pred_visitante", "pred_amarillas", "pred_rojas",
          "pred_var", "pred_penales_partido", "pred_minuto_gol",
          "pred_penales_local_tanda", "pred_penales_visitante_tanda"]

# Campos que existen en tabla apuesta con nombres exactos
CAMPO_BD = {
    "pred_local":                   "pred_local",
    "pred_visitante":               "pred_visitante",
    "pred_amarillas":               "pred_amarillas",
    "pred_rojas":                   "pred_rojas",
    "pred_var":                     "pred_var",
    "pred_penales_partido":         "pred_penales_partido",
    "pred_minuto_gol":              "pred_minuto_gol",
    "pred_penales_local_tanda":     "pred_penales_local_tanda",
    "pred_penales_visitante_tanda": "pred_penales_visitante_tanda",
}

actualizados = 0
sin_match_alias = set()
sin_match_partido = set()

for nf, ap_dict in sorted(excel_preds.items()):
    pid = partido_id_map.get(nf)
    if not pid:
        sin_match_partido.add(nf)
        continue

    for alias_ex, preds in ap_dict.items():
        # Match alias: directo o sin @
        alias_clean = alias_ex.lstrip('@').lower()
        apostador_id = alias_map.get(alias_clean) or alias_map.get(alias_ex.lower())
        if apostador_id is None:
            sin_match_alias.add(alias_ex)
            continue

        # Solo actualizar campos con valor no-None
        updates = {CAMPO_BD[k]: v for k, v in preds.items() if v is not None}
        if not updates:
            continue

        set_clause = ", ".join(f"{col} = %s" for col in updates)
        vals = list(updates.values()) + [apostador_id, pid]
        cur.execute(
            f"UPDATE apuesta SET {set_clause} WHERE apostador_id = %s AND partido_id = %s",
            vals
        )
        actualizados += cur.rowcount

conn.commit()
cur.close()
conn.close()

print(f"\n📊 Resultado:")
print(f"  Filas actualizadas: {actualizados}")
if sin_match_alias:
    print(f"  ⚠️  Aliases sin match BD ({len(sin_match_alias)}): {sorted(sin_match_alias)[:10]}")
if sin_match_partido:
    print(f"  ⚠️  Partidos no encontrados: {sorted(sin_match_partido)}")

print(f"\n✅ Listo. Ahora recalculá puntajes:")
print(f"   POST /api/v1/bets/calcular-puntajes/{TORNEO_ID}")
