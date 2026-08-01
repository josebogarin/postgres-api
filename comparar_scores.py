"""
comparar_scores.py
Compara puntajes en puntaje_detalle (BD) vs hoja Ranking del Excel generado.
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import sys, psycopg2, psycopg2.extras, openpyxl
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TORNEO_ID = 2
DB = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc")
EXCEL = _osp.path.join(_BASE, 'BECBUC_verificacion.xlsx')

# ── 1. Leer BD ────────────────────────────────────────────────────────────────
conn = psycopg2.connect(**DB)
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Puntaje partidos por apostador desde puntaje_detalle
cur.execute("""
    SELECT
        pd.apostador_id,
        -- buscar nombre desde apuesta
        MAX(a.nombre_apostador) AS nombre,
        SUM(COALESCE(pd.pts_resultado,0))       AS h,
        SUM(COALESCE(pd.pts_marcador,0))        AS i,
        SUM(COALESCE(pd.pts_amarillas,0))       AS j,
        SUM(COALESCE(pd.pts_rojas,0))           AS k,
        SUM(COALESCE(pd.pts_var,0))             AS l,
        SUM(COALESCE(pd.pts_penales_partido,0)) AS m,
        SUM(COALESCE(pd.pts_minuto,0))          AS n,
        SUM(COALESCE(pd.pts_penales_tanda,0))   AS o,
        SUM(COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
            COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
            COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
            COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0)) AS pts_partidos
    FROM puntaje_detalle pd
    LEFT JOIN apuesta a ON a.apostador_id = pd.apostador_id AND a.torneo_id = pd.torneo_id
    WHERE pd.torneo_id = %s
    GROUP BY pd.apostador_id
    ORDER BY pts_partidos DESC
""", (TORNEO_ID,))
db_rows = {int(r['apostador_id']): dict(r) for r in cur.fetchall()}

# Puntaje globales por apostador
cur.execute("""
    SELECT apostador_id,
           COALESCE(pts_campeon,0)+COALESCE(pts_finalistas,0)+COALESCE(pts_goleador,0)+
           COALESCE(pts_peor_equipo,0)+COALESCE(pts_mayor_goleada,0)+
           COALESCE(pts_etapa_paraguay,0)+COALESCE(pts_goles_paraguay,0) AS globales
    FROM puntaje_global WHERE torneo_id = %s
""", (TORNEO_ID,))
for r in cur.fetchall():
    aid = int(r['apostador_id'])
    if aid in db_rows:
        db_rows[aid]['globales'] = int(r['globales'])

conn.close()

for v in db_rows.values():
    v.setdefault('globales', 0)
    v['total'] = int(v['pts_partidos']) + int(v['globales'])

# ── 2. Leer Excel (hoja Ranking) ──────────────────────────────────────────────
wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
ws = wb['🏆 Ranking']

# Detectar columnas leyendo fila de header
headers = [str(c.value).strip() if c.value else '' for c in next(ws.rows)]
print(f"Headers Ranking: {headers[:15]}")

# Buscar cols: nombre, total
def hcol(name):
    for i, h in enumerate(headers):
        if name.lower() in h.lower():
            return i
    return -1

col_nombre = hcol('apostador') if hcol('apostador') >= 0 else hcol('nombre')
col_total  = hcol('total')
col_partidos = hcol('partidos')
col_globales = hcol('global')
col_h = hcol('result')
col_i = hcol('exact') if hcol('exact') >= 0 else hcol('marcador')
col_j = hcol('amari')
col_k = hcol('roja')
col_l = hcol('var')
col_m = hcol('penal') if 'penal' in ' '.join(headers).lower() else -1
col_n = hcol('minuto') if hcol('minuto') >= 0 else hcol('1er')

print(f"col_nombre={col_nombre}, col_total={col_total}, col_partidos={col_partidos}, col_globales={col_globales}")
print(f"col_h={col_h}, col_i={col_i}, col_j={col_j}, col_k={col_k}, col_l={col_l}, col_m={col_m}, col_n={col_n}")

excel_rows = {}
for row in ws.rows:
    cells = [c.value for c in row]
    if col_nombre < 0 or col_nombre >= len(cells):
        continue
    nombre = str(cells[col_nombre]).strip() if cells[col_nombre] else ''
    if not nombre or nombre.lower() in ('apostador', 'nombre', 'none', ''):
        continue

    def gv(col):
        if col < 0 or col >= len(cells): return 0
        v = cells[col]
        try: return int(v) if v is not None else 0
        except: return 0

    excel_rows[nombre.lower()] = {
        'nombre':    nombre,
        'total':     gv(col_total),
        'partidos':  gv(col_partidos),
        'globales':  gv(col_globales),
        'h': gv(col_h), 'i': gv(col_i), 'j': gv(col_j),
        'k': gv(col_k), 'l': gv(col_l), 'm': gv(col_m), 'n': gv(col_n),
    }

wb.close()
print(f"\nBD: {len(db_rows)} apostadores | Excel: {len(excel_rows)} filas\n")

# ── 3. Comparar ───────────────────────────────────────────────────────────────
print("=" * 100)
print(f"{'Apostador':<22} {'BD Total':>9} {'XL Total':>9} {'DIFF':>6}  │  "
      f"{'BD part':>7} {'XL part':>7} {'Dpart':>6}  │  "
      f"{'BD glob':>7} {'XL glob':>7} {'Dglob':>6}")
print("=" * 100)

diffs = []
for aid, bd in sorted(db_rows.items(), key=lambda x: -x[1]['total']):
    nombre_bd = (bd.get('nombre') or f'id={aid}').strip()

    # buscar en excel por nombre (case-insensitive, strip espacios)
    xl = excel_rows.get(nombre_bd.lower())
    if xl is None:
        # intento parcial
        for k, v in excel_rows.items():
            if nombre_bd.lower()[:6] in k:
                xl = v
                break

    bd_total  = int(bd['total'])
    bd_part   = int(bd['pts_partidos'])
    bd_glob   = int(bd['globales'])

    if xl:
        xl_total = xl['total']
        xl_part  = xl['partidos']
        xl_glob  = xl['globales']
    else:
        xl_total = xl_part = xl_glob = None

    diff_total = (bd_total - xl_total) if xl_total is not None else None
    diff_part  = (bd_part - xl_part) if xl_part is not None else None
    diff_glob  = (bd_glob - xl_glob) if xl_glob is not None else None

    has_diff = (diff_total not in (None, 0)) or (diff_part not in (None, 0)) or (diff_glob not in (None, 0))

    marker = " <<< DIFF" if has_diff else ""
    xl_total_s = str(xl_total) if xl_total is not None else "N/A"
    xl_part_s  = str(xl_part)  if xl_part  is not None else "N/A"
    xl_glob_s  = str(xl_glob)  if xl_glob  is not None else "N/A"
    diff_total_s = (f"{diff_total:+d}" if diff_total is not None else "N/A")
    diff_part_s  = (f"{diff_part:+d}"  if diff_part  is not None else "N/A")
    diff_glob_s  = (f"{diff_glob:+d}"  if diff_glob  is not None else "N/A")

    print(f"{nombre_bd:<22} {bd_total:>9} {xl_total_s:>9} {diff_total_s:>6}  │  "
          f"{bd_part:>7} {xl_part_s:>7} {diff_part_s:>6}  │  "
          f"{bd_glob:>7} {xl_glob_s:>7} {diff_glob_s:>6}{marker}")

    if has_diff or xl is None:
        diffs.append({'nombre': nombre_bd, 'aid': aid,
                      'diff_total': diff_total, 'diff_part': diff_part, 'diff_glob': diff_glob})

print("=" * 100)
print(f"\nTotal apostadores con diferencia: {len(diffs)}")
if diffs:
    print("\nRESUMEN DIFERENCIAS:")
    for d in diffs:
        print(f"  {d['nombre']:<22}  diff_total={d['diff_total']}  diff_part={d['diff_part']}  diff_glob={d['diff_glob']}")
