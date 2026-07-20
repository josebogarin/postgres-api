# -*- coding: utf-8 -*-
"""
fill_clasifica_null.py [--apply]
Rellena apuesta.pred_equipo_clasifica que quedo NULL en fases KO, tomando el valor
de la columna 'Q- QUIEN CLASIFICA' (col 32) de la hoja '50- TBL MASTER' del Excel
corregido. SOLO toca filas donde la BD tiene NULL (no pisa predicciones existentes).

SIN --apply: DRY RUN (muestra que rellenaria).
CON --apply: escribe en la BD (apuesta).

NOTA: tras --apply hay que recalcular -> run_recalc_force_grupos.bat
Solo lectura del Excel. Requiere psycopg2 (BD directa).
"""
import sys, os
args = [a.lower() for a in sys.argv[1:]]
DO_APPLY = '--apply' in args
print(f"{'[APPLY]' if DO_APPLY else '[DRY RUN]'}")

try:
    import openpyxl
except ImportError:
    os.system(f'"{sys.executable}" -m pip install openpyxl --quiet'); import openpyxl
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

BASE = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = None
_cands = [os.path.join(BASE, f) for f in os.listdir(BASE)
          if f.lower().endswith('.xlsx')
          and any(k in f.upper() for k in ('CORRECCIONES', 'SEMIFINAL', 'TBL PARA CARGAR'))]
def _rank(p):
    u = os.path.basename(p).upper()
    pref = 0 if 'CORRECCIONES' in u else (1 if 'SEMIFINAL' in u else 2)
    return (pref, -os.path.getmtime(p))
if _cands: EXCEL_FILE = sorted(_cands, key=_rank)[0]
if not EXCEL_FILE: sys.exit(f"ERROR: no se encontro Excel en {BASE}")
print(f"Excel: {os.path.basename(EXCEL_FILE)}")

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
CONN_APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
TID = 2
SHEET = '50- TBL MASTER'
KO_MIN = 73  # solo KO

conn = psycopg2.connect(CONN_BEC); conn.autocommit = False
capp = psycopg2.connect(CONN_APP)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cua = capp.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# alias -> uid
cua.execute("SELECT id, username FROM users WHERE is_active=TRUE")
uname = {u['username'].lower(): u['id'] for u in cua.fetchall()}
def clean_alias(s):
    if not s: return ''
    return str(s).replace('\xa0','').strip().upper().lstrip('@').replace('  ',' ')
def find_uid(al):
    a = clean_alias(al)
    for k, v in uname.items():
        if k.upper().lstrip('@') == a: return v
    for k, v in uname.items():
        if a and (a in k.upper() or k.upper() in a): return v
    return None

# equipo nombre -> id (normalizado, con y sin acentos)
import unicodedata
def norm(s):
    if s is None: return ''
    s = str(s).upper().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s
cur.execute("SELECT id, nombre, nombre_es FROM equipo")
eid = {}
for eq in cur.fetchall():
    for nm in (eq['nombre'], eq['nombre_es']):
        if nm: eid[norm(nm)] = eq['id']
_ALIAS_RAW = {'FRANCIA':'France','ESPANA':'Spain','ESPAÑA':'Spain','INGLATERRA':'England','ARGENTINA':'Argentina',
    'MARRUECOS':'Morocco','BELGICA':'Belgium','NORUEGA':'Norway','SUIZA':'Switzerland',
    'COLOMBIA':'Colombia','MEXICO':'Mexico','BRASIL':'Brazil','PORTUGAL':'Portugal',
    'PARAGUAY':'Paraguay','CANADA':'Canada','EGIPTO':'Egypt','ESTADOS UNIDOS':'USA',
    'EE UU':'USA','EEUU':'USA','ALEMANIA':'Germany','PAISES BAJOS':'Netherlands',
    'HOLANDA':'Netherlands','SUDAFRICA':'South Africa','JAPON':'Japan','SUECIA':'Sweden',
    'COSTA DE MARFIL':'Ivory Coast','COSTA MARFIL':'Ivory Coast','ARGELIA':'Algeria',
    'CROACIA':'Croatia','SENEGAL':'Senegal','AUSTRIA':'Austria','BELGICA ':'Belgium'}
# keys normalizadas (sin acentos)
ALIAS_N = {norm(k): v for k, v in _ALIAS_RAW.items()}
def find_eid(txt):
    if txt is None: return None
    k = norm(txt)
    if k in ('', 'NONE', '-'): return None
    if k in eid: return eid[k]
    a = ALIAS_N.get(k)
    if a and norm(a) in eid: return eid[norm(a)]
    for kk, vv in eid.items():
        if k and (k in kk or kk in k): return vv
    return None

# partido nf -> id
cur.execute("""SELECT p.numero_fifa, p.id FROM partido p JOIN fase f ON f.id=p.fase_id
               WHERE f.torneo_id=%s""", (TID,))
pid_by_nf = {r['numero_fifa']: r['id'] for r in cur.fetchall()}

# apuestas con pred_equipo_clasifica NULL en KO
cur.execute("""SELECT a.apostador_id, p.numero_fifa
               FROM apuesta a JOIN partido p ON p.id=a.partido_id JOIN fase f ON f.id=p.fase_id
               WHERE f.torneo_id=%s AND p.numero_fifa >= %s AND a.pred_equipo_clasifica IS NULL""",
            (TID, KO_MIN))
null_set = {(r['apostador_id'], r['numero_fifa']) for r in cur.fetchall()}
print(f"Filas KO con pred_equipo_clasifica NULL en BD: {len(null_set)}")

# leer Excel col 32
COL = dict(pid=2, alias=10, q=32)
wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True, read_only=True)
ws = wb[SHEET]
to_fill = []   # (uid, nf, eid, txt)
sin_map_uid = set(); sin_map_eq = set()
for row in ws.iter_rows(min_row=2, values_only=True):
    pid = row[COL['pid']-1]
    if not (isinstance(pid, str) and pid.startswith('P')): continue
    try: nf = int(pid[1:])
    except: continue
    if nf < KO_MIN: continue
    uid = find_uid(row[COL['alias']-1])
    if uid is None:
        sin_map_uid.add(clean_alias(row[COL['alias']-1])); continue
    if (uid, nf) not in null_set: continue   # solo rellenar NULL
    txt = row[COL['q']-1]
    e = find_eid(txt)
    if e is None:
        if txt not in (None,'','-'): sin_map_eq.add(str(txt))
        continue
    to_fill.append((uid, nf, e, txt))

print(f"A rellenar (NULL en BD + valor en Excel): {len(to_fill)}")
if sin_map_uid: print(f"  alias sin match: {sorted(x for x in sin_map_uid if x)[:10]}")
if sin_map_eq:  print(f"  equipos sin match: {sorted(sin_map_eq)[:15]}")

# muestra
for uid, nf, e, txt in to_fill[:20]:
    print(f"  uid={uid} P{nf:03d} -> {txt} (equipo_id={e})")
if len(to_fill) > 20: print(f"  ... (+{len(to_fill)-20} mas)")

if DO_APPLY and to_fill:
    n = 0
    for uid, nf, e, txt in to_fill:
        p = pid_by_nf.get(nf)
        if not p: continue
        cur.execute("""UPDATE apuesta SET pred_equipo_clasifica=%s
                       WHERE apostador_id=%s AND partido_id=%s AND pred_equipo_clasifica IS NULL""",
                    (e, uid, p))
        n += cur.rowcount
    conn.commit()
    print(f"\n[APPLY] Filas actualizadas: {n}")
    print("Ahora corré run_recalc_force_grupos.bat para re-puntuar.")
elif to_fill:
    print("\n[DRY RUN] No se escribio. Para aplicar: fill_clasifica_null.py --apply")
conn.close(); capp.close()
