# -*- coding: utf-8 -*-
"""
resubir_octavos_sanbie_pato.py
Re-sube (upsert) las apuestas de OCTAVOS (P089-P096) de sanbie y pato desde el
Excel master '50- TBL MASTER' (archivo "TBL PARA SUBIR AL LIVE"), que el usuario
confirma como fuente correcta.

Uso:
  backend\.venv\Scripts\python.exe resubir_octavos_sanbie_pato.py           <- DRY RUN
  backend\.venv\Scripts\python.exe resubir_octavos_sanbie_pato.py --import  <- ESCRIBE
"""
import sys, os, glob
BASE = os.path.dirname(os.path.abspath(__file__))

ALIASES = {'SANBIE', 'PATO'}     # se resuelven a apostador_id via app_db username
DO_IMPORT = '--import' in sys.argv
TORNEO_ID = 2

# Excel: preferir el "SUBIR AL LIVE"; fallback a cualquiera con hoja 50- TBL MASTER
EXCEL_FILE = None
for f in os.listdir(BASE):
    if f.endswith('.xlsx') and 'SUBIR AL LIVE' in f.upper():
        EXCEL_FILE = os.path.join(BASE, f); break
if not EXCEL_FILE:
    sys.exit("ERROR: no se encontro el Excel *SUBIR AL LIVE*.xlsx en la carpeta del proyecto.")
print(f"Excel: {os.path.basename(EXCEL_FILE)}")

try: import openpyxl
except ImportError: os.system(f'"{sys.executable}" -m pip install openpyxl --quiet'); import openpyxl
try: import psycopg2, psycopg2.extras
except ImportError: os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
CONN_APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
conn_bec = psycopg2.connect(CONN_BEC); conn_app = psycopg2.connect(CONN_APP)
cur_bec = conn_bec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur_app = conn_app.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── apostador ids ─────────────────────────────────────────────────────────────
cur_app.execute("SELECT id, username FROM users WHERE lower(username) IN ('sanbie','pato')")
uid_by_user = {r['username'].lower(): r['id'] for r in cur_app.fetchall()}
if 'sanbie' not in uid_by_user or 'pato' not in uid_by_user:
    sys.exit(f"ERROR: no se resolvieron sanbie/pato -> {uid_by_user}")
alias_to_uid = {'SANBIE': uid_by_user['sanbie'], 'PATO': uid_by_user['pato']}
print(f"sanbie -> id={uid_by_user['sanbie']}   pato -> id={uid_by_user['pato']}")

# ── equipos ───────────────────────────────────────────────────────────────────
cur_bec.execute("SELECT id, nombre, nombre_es FROM equipo")
eqmap = {}
for e in cur_bec.fetchall():
    if e['nombre']:    eqmap[e['nombre'].upper().strip()] = e['id']
    if e['nombre_es']: eqmap[e['nombre_es'].upper().strip()] = e['id']
EQ_ALIAS = {'PARAGUAY':'Paraguay','FRANCIA':'France','CANADA':'Canada','MARRUECOS':'Morocco',
    'BRASIL':'Brazil','NORUEGA':'Norway','MEXICO':'Mexico','INGLATERRA':'England','PORTUGAL':'Portugal',
    'ESPAÑA':'Spain','ESPANA':'Spain','ESTADOS UNIDOS':'USA','BELGICA':'Belgium','ARGENTINA':'Argentina',
    'EGIPTO':'Egypt','SUIZA':'Switzerland','COLOMBIA':'Colombia'}
def eqid(nombre):
    if not nombre: return None
    k = str(nombre).upper().strip()
    if k in eqmap: return eqmap[k]
    a = EQ_ALIAS.get(k)
    if a and a.upper() in eqmap: return eqmap[a.upper()]
    for kk, vv in eqmap.items():
        if k in kk or kk in k: return vv
    return None

# ── partidos octavos ──────────────────────────────────────────────────────────
cur_bec.execute("""
    SELECT p.id, p.numero_fifa FROM partido p JOIN fase f ON f.id=p.fase_id
    WHERE f.torneo_id=%s AND p.numero_fifa BETWEEN 89 AND 96 ORDER BY p.numero_fifa
""", (TORNEO_ID,))
pid_by_pcode = {f"P{r['numero_fifa']:03d}": r['id'] for r in cur_bec.fetchall()}

def clean(s): return str(s).replace('\xa0','').strip().upper() if s else ''
def toi(v):
    try:
        s=str(v).strip()
        if s in ('','-','None'): return None
        return int(float(s))
    except: return None

wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True); ws = wb['50- TBL MASTER']
preds=[]
for r in range(2, ws.max_row+1):
    if str(ws.cell(r,7).value)!='30- OCTAVOS': continue
    al=clean(ws.cell(r,10).value)
    if al not in ALIASES: continue
    pcode=str(ws.cell(r,2).value).strip()
    pid=pid_by_pcode.get(pcode)
    if not pid: continue
    clas = ws.cell(r,32).value
    preds.append({
        'apostador_id': alias_to_uid[al], 'partido_id': pid,
        'pred_local': toi(ws.cell(r,13).value) or 0,
        'pred_visitante': toi(ws.cell(r,15).value) or 0,
        'pred_amarillas': toi(ws.cell(r,25).value),
        'pred_rojas': toi(ws.cell(r,26).value),
        'pred_var': toi(ws.cell(r,27).value),
        'pred_penales_partido': toi(ws.cell(r,28).value),
        'pred_minuto_gol': toi(ws.cell(r,29).value),
        'pred_penales_local_tanda': toi(ws.cell(r,30).value),
        'pred_penales_visitante_tanda': toi(ws.cell(r,31).value),
        'pred_equipo_clasifica': eqid(clas),
        '_alias': al, '_pcode': pcode, '_clas': clas,
    })

print(f"\nFilas a re-subir: {len(preds)} (esperado 2 x 8 = 16)")
for p in sorted(preds, key=lambda x:(x['_alias'],x['_pcode'])):
    print(f"  {p['_alias']:<7} {p['_pcode']} {p['pred_local']}-{p['pred_visitante']}"
          f" J{p['pred_amarillas']} K{p['pred_rojas']} L{p['pred_var']} M{p['pred_penales_partido']}"
          f" N{p['pred_minuto_gol']} T{p['pred_penales_local_tanda']}/{p['pred_penales_visitante_tanda']}"
          f" Cls={p['_clas']}({p['pred_equipo_clasifica']})")

if not DO_IMPORT:
    print("\n[DRY RUN] No se escribio. Para aplicar: --import")
    sys.exit(0)

up=err=0
for p in preds:
    try:
        cur_bec.execute("""
          INSERT INTO apuesta (apostador_id, partido_id, pred_local, pred_visitante,
            pred_amarillas, pred_rojas, pred_var, pred_penales_partido, pred_minuto_gol,
            pred_penales_local_tanda, pred_penales_visitante_tanda, pred_equipo_clasifica)
          VALUES (%(apostador_id)s,%(partido_id)s,%(pred_local)s,%(pred_visitante)s,
            %(pred_amarillas)s,%(pred_rojas)s,%(pred_var)s,%(pred_penales_partido)s,%(pred_minuto_gol)s,
            %(pred_penales_local_tanda)s,%(pred_penales_visitante_tanda)s,%(pred_equipo_clasifica)s)
          ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
            pred_local=EXCLUDED.pred_local, pred_visitante=EXCLUDED.pred_visitante,
            pred_amarillas=EXCLUDED.pred_amarillas, pred_rojas=EXCLUDED.pred_rojas,
            pred_var=EXCLUDED.pred_var, pred_penales_partido=EXCLUDED.pred_penales_partido,
            pred_minuto_gol=EXCLUDED.pred_minuto_gol,
            pred_penales_local_tanda=EXCLUDED.pred_penales_local_tanda,
            pred_penales_visitante_tanda=EXCLUDED.pred_penales_visitante_tanda,
            pred_equipo_clasifica=EXCLUDED.pred_equipo_clasifica
        """, p)
        up+=1
    except Exception as e:
        err+=1; conn_bec.rollback(); print(f"  ERROR {p['_alias']} {p['_pcode']}: {e}")
conn_bec.commit()
print(f"\nRe-subidas: {up}  Errores: {err}")
print("Luego recalcular: POST /calcular-puntajes/2")
conn_bec.close(); conn_app.close()
