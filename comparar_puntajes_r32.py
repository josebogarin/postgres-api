"""
comparar_puntajes_r32.py
============================
Compara puntajes R32 (P073-P088) entre:
  - Hoja "50- TBL MASTER" del Excel TBL CHECK
  - tabla puntaje_detalle de la BD becbuc

Items comparados: H, I, J, K, L, M, N, O

Ejecutar:
  cd "C:\proyecto FAST API"
  $excel = "C:\...\20260702- TBL CHECK PARA JOSE.xlsx"
  backend\.venv\Scripts\python.exe comparar_puntajes_r32.py $excel
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

# ── Estructura hoja 50- TBL MASTER ───────────────────────────────────────────
# col[1]=ID PARTIDO, col[9]=ALIAS, col[54]=ESTADO
# col[39]=H, [40]=I, [41]=J, [42]=K, [43]=L, [44]=M, [45]=N
# col[46]=O-EQ1(tanda local), [47]=O-EQ2(tanda visitante)
COLS = {"H": 39, "I": 40, "J": 41, "K": 42, "L": 43, "M": 44, "N": 45,
        "Ol": 46, "Ov": 47}

def iv(v):
    try:    return int(v)
    except: return 0

# ── 1. Leer Excel ─────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True, read_only=True)
ws = wb["50- TBL MASTER"]

excel_data    = collections.defaultdict(dict)  # [nf][alias] = {H..O}
skipped_pend  = set()

for row in ws.iter_rows(min_row=2, values_only=True):
    pid = row[1]
    if not pid or not str(pid).startswith('P'):
        continue
    try:
        nf = int(str(pid)[1:])
    except:
        continue
    if not (73 <= nf <= 88):
        continue

    estado = str(row[54]).strip().upper() if row[54] else ''
    if estado != 'FINALIZADO':
        skipped_pend.add(nf)
        continue

    alias = str(row[9]).strip().lstrip('\xa0').lstrip()
    if not alias:
        continue

    pts = {k: iv(row[c]) for k, c in COLS.items()}
    pts["O"] = pts["Ol"] + pts["Ov"]
    excel_data[nf][alias] = pts

finalizados = sorted(excel_data.keys())
print(f"✅ Excel: {len(finalizados)} partidos R32 finalizados, "
      f"{len(skipped_pend)} pendientes: {sorted(skipped_pend)}")
n_ap = len(set(a for d in excel_data.values() for a in d))
print(f"   Apostadores por partido: ~{n_ap}\n")

# ── 2. Alias map desde app_db ─────────────────────────────────────────────────
conn_app = psycopg2.connect(**APP_DB)
cur_app  = conn_app.cursor()
cur_app.execute("""
    SELECT u.id, u.username
    FROM users u
    JOIN user_roles ur ON ur.user_id = u.id
    JOIN roles ro ON ro.id = ur.role_id
    WHERE ro.name = 'apostador' AND u.is_active = TRUE
""")
alias_map = {row[0]: row[1] for row in cur_app.fetchall()}
cur_app.close()
conn_app.close()

# ── 3. Puntajes BD desde becbuc ───────────────────────────────────────────────
conn = psycopg2.connect(**BECBUC_DB)
cur  = conn.cursor()
cur.execute("""
    SELECT pd.apostador_id, p.numero_fifa,
           COALESCE(pd.pts_resultado,       0) AS H,
           COALESCE(pd.pts_marcador,        0) AS I,
           COALESCE(pd.pts_amarillas,       0) AS J,
           COALESCE(pd.pts_rojas,           0) AS K,
           COALESCE(pd.pts_var,             0) AS L,
           COALESCE(pd.pts_penales_partido, 0) AS M,
           COALESCE(pd.pts_minuto,          0) AS N,
           COALESCE(pd.pts_penales_tanda,   0) AS O
    FROM puntaje_detalle pd
    JOIN partido p ON p.id = pd.partido_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = %s
      AND p.numero_fifa BETWEEN 73 AND 88
""", (TORNEO_ID,))

bd_data = collections.defaultdict(dict)  # [nf][alias] = {H..O}
for aid, nf, H, I, J, K, L, M, N, O in cur.fetchall():
    alias = alias_map.get(aid, f"id{aid}")
    bd_data[nf][alias] = {"H": H, "I": I, "J": J, "K": K,
                          "L": L, "M": M, "N": N, "O": O}

cur.close()
conn.close()

bd_total_filas = sum(len(v) for v in bd_data.values())
print(f"✅ BD: {len(bd_data)} partidos R32, {bd_total_filas} filas puntaje_detalle\n")

# ── 4. Comparar ───────────────────────────────────────────────────────────────
ITEMS = ["H", "I", "J", "K", "L", "M", "N", "O"]
diffs = []
total_rows = 0
item_counts = {k: 0 for k in ITEMS}

for nf in finalizados:
    ex_part = excel_data[nf]
    bd_part = bd_data.get(nf, {})

    # Normalizar alias Excel: buscar coincidencia por substring con alias BD
    # El Excel usa "@BS", BD usa "bs" o similar → intentar match directo primero
    for alias_ex, ex_pts in sorted(ex_part.items()):
        # Buscar alias en BD (case-insensitive, strip @)
        alias_clean = alias_ex.lstrip('@').lower()
        alias_bd = None
        for a in bd_part:
            if a.lower() == alias_clean or a.lower() == alias_ex.lower():
                alias_bd = a
                break
        if alias_bd is None:
            # Intento por substring
            for a in bd_part:
                if alias_clean in a.lower() or a.lower() in alias_clean:
                    alias_bd = a
                    break

        bd_pts = bd_part.get(alias_bd, {}) if alias_bd else {}
        total_rows += 1

        for item in ITEMS:
            ev = ex_pts.get(item, 0)
            bv = bd_pts.get(item, 0)
            if ev != bv:
                diffs.append((nf, alias_ex, item, ev, bv))
                item_counts[item] += 1

# ── 5. Reporte ────────────────────────────────────────────────────────────────
print(f"{'='*60}")
print(f"RESUMEN: {total_rows} filas | {len(diffs)} diferencias")
print(f"{'='*60}")
print("Diffs por ítem:", "  ".join(f"{k}={v}" for k, v in item_counts.items()))
print(f"TOTAL DIFFS: {len(diffs)}\n")

if diffs:
    print(f"{'P#':<6} {'Alias':<20} {'Item':<5} {'Excel':>6} {'BD':>6}")
    print("-" * 50)
    for nf, alias, item, ev, bv in diffs:
        marker = "BD>" if bv > ev else "EX>"
        print(f"P{nf:03d}  {alias:<20} {item:<5} {ev:>6} {bv:>6}  ({marker})")
else:
    print("✅ PERFECTO: BD y Excel R32 coinciden en todos los ítems H-O")

# ── 6. Totales por partido ────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("TOTALES H-O POR PARTIDO (suma todos los apostadores)")
print(f"{'P#':<8} {'Excel':>8} {'BD':>8} {'Diff':>8}")
print("-" * 35)
grand_ex = grand_bd = 0
for nf in finalizados:
    ex_tot = sum(sum(p.get(k, 0) for k in ITEMS) for p in excel_data[nf].values())
    bd_tot = sum(sum(p.get(k, 0) for k in ITEMS) for p in bd_data.get(nf, {}).values())
    grand_ex += ex_tot; grand_bd += bd_tot
    marker = " ←" if ex_tot != bd_tot else ""
    print(f"P{nf:03d}     {ex_tot:>8} {bd_tot:>8} {bd_tot-ex_tot:>+8}{marker}")
print(f"{'TOTAL':<8} {grand_ex:>8} {grand_bd:>8} {grand_bd-grand_ex:>+8}")
