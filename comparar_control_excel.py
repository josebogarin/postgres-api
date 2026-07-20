"""
comparar_control_excel.py
Compara puntajes puntaje_detalle (BD) vs Excel de Control por apostador y partido.

Uso:
  backend\.venv\Scripts\python.exe -u comparar_control_excel.py > comparar_control_log.txt 2>&1
"""
import sys, psycopg2, psycopg2.extras, openpyxl
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TORNEO_ID = 2
DB = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc")

# Ruta del Excel de control (uploads de la sesion actual)
UPLOADS_BASE = Path(r"C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions")
# Buscar el Excel de control entre todos los uploads
CONTROL_EXCEL = None
for p in UPLOADS_BASE.rglob("*ranking_torneo2_20260624_1241.xlsx"):
    CONTROL_EXCEL = p
    break

if not CONTROL_EXCEL:
    # Fallback: buscar por UUID
    for p in UPLOADS_BASE.rglob("8f7cd0c4-ranking_torneo2_20260624_1241.xlsx"):
        CONTROL_EXCEL = p
        break

if not CONTROL_EXCEL:
    print("ERROR: No se encontro el Excel de control en uploads")
    sys.exit(1)

print(f"Excel control: {CONTROL_EXCEL}")

# ─────────────────────────────────────────────────────────────
# 1. Leer BD: puntaje_detalle por (apostador, partido)
# ─────────────────────────────────────────────────────────────
conn = psycopg2.connect(**DB)
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Obtener numeros de partido (numero o numero_fifa)
cur.execute("""
    SELECT p.id AS partido_id,
           COALESCE(p.numero_fifa, p.id) AS numero,
           COALESCE(el.nombre_es, el.nombre) AS local,
           COALESCE(ev.nombre_es, ev.nombre) AS visitante,
           p.goles_local,
           p.goles_visitante,
           p.estado,
           f.nombre AS fase_nombre
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id = %s
    ORDER BY COALESCE(p.numero_fifa, p.id)
""", (TORNEO_ID,))
partidos_bd = {int(r['numero']): dict(r) for r in cur.fetchall()}
partido_id_to_num = {v['partido_id']: k for k, v in partidos_bd.items()}
print(f"BD: {len(partidos_bd)} partidos cargados")

# Obtener puntaje_detalle por (apostador_id, partido_id)
cur.execute("""
    SELECT pd.apostador_id,
           MAX(a.nombre_apostador) AS nombre,
           pd.partido_id,
           COALESCE(pd.pts_resultado, 0)       AS h,
           COALESCE(pd.pts_marcador, 0)        AS i,
           COALESCE(pd.pts_amarillas, 0)       AS j,
           COALESCE(pd.pts_rojas, 0)           AS k,
           COALESCE(pd.pts_var, 0)             AS l,
           COALESCE(pd.pts_penales_partido, 0) AS m,
           COALESCE(pd.pts_minuto, 0)          AS n,
           COALESCE(pd.pts_penales_tanda, 0)   AS o,
           COALESCE(pd.pts_resultado, 0) + COALESCE(pd.pts_marcador, 0) +
           COALESCE(pd.pts_amarillas, 0) + COALESCE(pd.pts_rojas, 0) +
           COALESCE(pd.pts_var, 0) + COALESCE(pd.pts_penales_partido, 0) +
           COALESCE(pd.pts_minuto, 0) + COALESCE(pd.pts_penales_tanda, 0) AS total
    FROM puntaje_detalle pd
    LEFT JOIN apuesta a ON a.apostador_id = pd.apostador_id
    WHERE pd.torneo_id = %s
    GROUP BY pd.apostador_id, pd.partido_id
""", (TORNEO_ID,))

# Indexar por (nombre_lower, numero_partido)
bd_por_key = {}  # (nombre_lower, partido_num) -> dict
bd_nombres = {}  # apostador_id -> nombre
for r in cur.fetchall():
    r = dict(r)
    pid = r['partido_id']
    num = partido_id_to_num.get(pid)
    if num is None:
        continue
    nombre = (r['nombre'] or f"id={r['apostador_id']}").strip()
    bd_nombres[r['apostador_id']] = nombre
    bd_por_key[(nombre.lower(), num)] = r

conn.close()
print(f"BD: {len(bd_por_key)} filas puntaje_detalle cargadas")

# ─────────────────────────────────────────────────────────────
# 2. Leer Excel de control: todas las hojas Grupo *
# ─────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook(str(CONTROL_EXCEL), read_only=True, data_only=True)
grupo_sheets = [s for s in wb.sheetnames if s.startswith('Grupo')]

xl_por_key = {}  # (nombre_lower, partido_num) -> dict
for sheet_name in grupo_sheets:
    ws = wb[sheet_name]
    for i, row in enumerate(ws.rows):
        if i < 2:
            continue  # skip 2 header rows
        cells = [c.value for c in row]
        if not cells[0] or not cells[1]:
            continue
        apostador = str(cells[0]).strip()
        partido_raw = str(cells[1]).strip()
        num_str = partido_raw.split()[0]  # 'P1'
        try:
            num = int(num_str[1:])
        except:
            continue
        xl_por_key[(apostador.lower(), num)] = {
            'apostador': apostador,
            'partido': partido_raw,
            'partido_num': num,
            'marc_pred': cells[2],
            'marc_real': cells[3],
            'h': int(cells[4] or 0),
            'i': int(cells[5] or 0),
            'j': int(cells[8] or 0),
            'k': int(cells[11] or 0),
            'l': int(cells[14] or 0),
            'm': int(cells[17] or 0),
            'n': int(cells[20] or 0),
            'o': int(cells[25] or 0),
            'total': int(cells[26] or 0),
        }

wb.close()
print(f"Excel: {len(xl_por_key)} filas cargadas de {len(grupo_sheets)} hojas")

# ─────────────────────────────────────────────────────────────
# 3. Comparar fila a fila
# ─────────────────────────────────────────────────────────────
items = ['h', 'i', 'j', 'k', 'l', 'm', 'n', 'o']
diffs_por_apostador = defaultdict(list)  # nombre -> list de diffs
diffs_por_item = defaultdict(int)  # item -> count diffs

total_filas = 0
total_match = 0
total_diff = 0
solo_en_bd = 0
solo_en_xl = 0

# Compare BD -> Excel
for (nombre_l, num), bd in bd_por_key.items():
    total_filas += 1
    xl = xl_por_key.get((nombre_l, num))
    if xl is None:
        # buscar nombre parcial
        for (nl, n2), v in xl_por_key.items():
            if n2 == num and (nombre_l[:6] in nl or nl[:6] in nombre_l):
                xl = v
                break
    if xl is None:
        solo_en_bd += 1
        continue

    row_diff = {}
    for item in items:
        bd_val = int(bd[item])
        xl_val = int(xl[item])
        if bd_val != xl_val:
            row_diff[item] = (bd_val, xl_val, bd_val - xl_val)
            diffs_por_item[item] += 1

    if row_diff:
        total_diff += 1
        nombre_bd = bd['nombre'] or nombre_l
        p_info = partidos_bd.get(num, {})
        diffs_por_apostador[nombre_bd].append({
            'partido_num': num,
            'partido': xl['partido'],
            'marc_pred_xl': xl['marc_pred'],
            'marc_real_xl': xl['marc_real'],
            'diffs': row_diff,
        })
    else:
        total_match += 1

# Detectar filas solo en Excel
for (nombre_l, num) in xl_por_key:
    # Buscar en BD
    if (nombre_l, num) not in bd_por_key:
        found = False
        for (nl2, n2) in bd_por_key:
            if n2 == num and (nombre_l[:6] in nl2 or nl2[:6] in nombre_l):
                found = True
                break
        if not found:
            solo_en_xl += 1

# ─────────────────────────────────────────────────────────────
# 4. Reporte
# ─────────────────────────────────────────────────────────────
print()
print("=" * 120)
print(f"COMPARACION BD vs Excel Control | Total BD: {len(bd_por_key)} | Total XL: {len(xl_por_key)}")
print(f"Match exacto: {total_match} | Con diferencias: {total_diff} | Solo BD: {solo_en_bd} | Solo XL: {solo_en_xl}")
print("=" * 120)

print("\n--- DIFERENCIAS POR ITEM ---")
for item in items:
    cnt = diffs_por_item.get(item, 0)
    if cnt > 0:
        label = {'h':'H(Res)', 'i':'I(Exact)', 'j':'J(Amar)', 'k':'K(Rojas)',
                 'l':'L(VAR)', 'm':'M(Pen.Pto)', 'n':'N(Minuto)', 'o':'O(Tanda)'}[item]
        print(f"  {label:<15}: {cnt} filas con diferencia")

print("\n--- DETALLE POR APOSTADOR ---")
for nombre, lista in sorted(diffs_por_apostador.items()):
    print(f"\n{'='*80}")
    print(f"APOSTADOR: {nombre}  ({len(lista)} partidos con diferencias)")
    print(f"{'P#':<4} {'Partido':<35} {'Pred':<8} {'Real':<8} {'Item':<12} {'BD':>4} {'XL':>4} {'DIFF':>5}")
    print(f"{'-'*4} {'-'*35} {'-'*8} {'-'*8} {'-'*12} {'-'*4} {'-'*4} {'-'*5}")
    for d in sorted(lista, key=lambda x: x['partido_num']):
        first = True
        for item, (bd_v, xl_v, diff) in sorted(d['diffs'].items()):
            label = {'h':'H(Res)', 'i':'I(Exact)', 'j':'J(Amar)', 'k':'K(Rojas)',
                     'l':'L(VAR)', 'm':'M(Pen.Pto)', 'n':'N(Minuto)', 'o':'O(Tanda)'}[item]
            pred = d['marc_pred_xl'] or '-'
            real = d['marc_real_xl'] or '-'
            if first:
                print(f"P{d['partido_num']:<3} {d['partido'][:35]:<35} {str(pred):<8} {str(real):<8} {label:<12} {bd_v:>4} {xl_v:>4} {diff:>+5}")
                first = False
            else:
                print(f"{'':4} {'':35} {'':8} {'':8} {label:<12} {bd_v:>4} {xl_v:>4} {diff:>+5}")

print("\n" + "=" * 120)
print("FIN COMPARACION")

# ─────────────────────────────────────────────────────────────
# 5. Resumen global de diferencias por apostador
# ─────────────────────────────────────────────────────────────
print("\n--- RESUMEN DIFERENCIAS POR APOSTADOR (partidos afectados) ---")
print(f"{'Apostador':<25} {'Partidos c/diff':>15} {'Items afectados'}")
print("-" * 70)
for nombre in sorted(diffs_por_apostador, key=lambda n: -len(diffs_por_apostador[n])):
    lista = diffs_por_apostador[nombre]
    items_cnt = defaultdict(int)
    for d in lista:
        for item in d['diffs']:
            items_cnt[item] += 1
    items_str = ', '.join(f"{k.upper()}:{v}" for k,v in sorted(items_cnt.items()))
    print(f"{nombre:<25} {len(lista):>15}  {items_str}")
