"""
importar_8vos_excel.py  — Sesion 60
Importa pronosticos 8vos de final (P089-P096) desde el Excel consolidado.
Bloquea la fase ronda32 antes de importar.

Uso:
  run_importar_8vos.bat               <- dry run (solo verifica)
  run_importar_8vos.bat --import      <- importa y bloquea R32
"""

import sys, os, glob

BASE = os.path.dirname(os.path.abspath(__file__))

# Buscar el Excel de 8vos
EXCEL_FILE = None
for f in os.listdir(BASE):
    fu = f.upper()
    if ('8VOS' in fu or 'OCTAVOS' in fu) and f.endswith('.xlsx'):
        EXCEL_FILE = os.path.join(BASE, f)
        break

if not EXCEL_FILE:
    print("ERROR: No se encontro el Excel de 8vos.")
    print(f"Copia el archivo '...8vos.xlsx' a: {BASE}")
    sys.exit(1)

print(f"Excel: {os.path.basename(EXCEL_FILE)}")

try:
    import openpyxl
except ImportError:
    os.system(f'"{sys.executable}" -m pip install openpyxl --quiet')
    import openpyxl

try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet')
    import psycopg2, psycopg2.extras

CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
CONN_APP = "host=localhost port=5432 dbname=app_db  user=app_user password=superpassword"
TORNEO_ID = 2
DO_IMPORT = '--import' in sys.argv

print("Conectando a BD...")
try:
    conn_bec = psycopg2.connect(CONN_BEC)
    conn_app = psycopg2.connect(CONN_APP)
except Exception as e:
    print(f"ERROR de conexion: {e}")
    print("Asegurate de que Docker este corriendo: docker start core-postgres")
    sys.exit(1)

cur_bec = conn_bec.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur_app = conn_app.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ── Cargar usuarios desde app_db ──────────────────────────────────────────────
cur_app.execute("SELECT id, username FROM users WHERE is_active=TRUE ORDER BY id")
all_users = cur_app.fetchall()

# IDs que ya tienen apuestas en becbuc (apostadores activos)
cur_bec.execute("""
    SELECT DISTINCT a.apostador_id
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = %s
""", (TORNEO_ID,))
bec_ids = {r['apostador_id'] for r in cur_bec.fetchall()}

bd_apostadores = [u for u in all_users if u['id'] in bec_ids]
apostador_to_id = {u['username'].lower(): u['id'] for u in bd_apostadores}
print(f"Apostadores en BD: {len(bd_apostadores)}")

# ── Mapeo de equipos (nombre ES → equipo_id) ─────────────────────────────────
cur_bec.execute("SELECT id, nombre, nombre_es FROM equipo")
equipos_rows = cur_bec.fetchall()
equipo_id_by_nombre = {}
for eq in equipos_rows:
    if eq['nombre']:
        equipo_id_by_nombre[eq['nombre'].upper().strip()] = eq['id']
    if eq['nombre_es']:
        equipo_id_by_nombre[eq['nombre_es'].upper().strip()] = eq['id']

# Aliases adicionales para nombres que difieren entre Excel y BD
EQUIPO_ALIAS = {
    'ESTADOS UNIDOS': 'USA',
    'BELGICA':        'Belgium',
    'BELGICA':        'BELGICA',
    'MARRUECOS':      'Morocco',
    'NORUEGA':        'Norway',
    'ENGLAND':        'England',
    'COLOMBIA':       'Colombia',
    'SUIZA':          'Switzerland',
    'ESPAÑA':         'Spain',
    'PORTUGAL':       'Portugal',
    'BRASIL':         'Brazil',
    'ARGENTINA':      'Argentina',
    'EGIPTO':         'Egypt',
    'MEXICO':         'Mexico',
    'CANADA':         'Canada',
    'FRANCIA':        'France',
    'PARAGUAU':       'Paraguay',
}

def find_equipo_id(nombre_excel):
    if not nombre_excel:
        return None
    key = str(nombre_excel).upper().strip()
    if key in equipo_id_by_nombre:
        return equipo_id_by_nombre[key]
    # intentar via alias
    alt = EQUIPO_ALIAS.get(key)
    if alt:
        return equipo_id_by_nombre.get(alt.upper().strip())
    # búsqueda parcial
    for k, v in equipo_id_by_nombre.items():
        if key in k or k in key:
            return v
    return None

# ── Partidos 8vos en BD ───────────────────────────────────────────────────────
cur_bec.execute("""
    SELECT p.id, p.numero_fifa,
           el.nombre AS local_nombre, ev.nombre AS visitante_nombre,
           p.estado
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id = %s AND p.numero_fifa BETWEEN 89 AND 96
    ORDER BY p.numero_fifa
""", (TORNEO_ID,))
partidos_8vos = {f"P{r['numero_fifa']:03d}": dict(r) for r in cur_bec.fetchall()}
print(f"\nPartidos 8vos en BD ({len(partidos_8vos)}):")
for k, v in sorted(partidos_8vos.items()):
    print(f"  {k} id={v['id']}: {v['local_nombre']} vs {v['visitante_nombre']} [{v['estado']}]")

# ── Fases ronda32 para bloquear ───────────────────────────────────────────────
cur_bec.execute("""
    SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
    FROM fase
    WHERE torneo_id = %s AND tipo ILIKE 'ronda32'
    ORDER BY id
""", (TORNEO_ID,))
fases_r32 = cur_bec.fetchall()
print(f"\nFases R32 ({len(fases_r32)}):")
for f in fases_r32:
    estado_b = '✅ YA BLOQUEADA' if f['bloqueada'] else '🔓 SIN BLOQUEAR'
    print(f"  id={f['id']} [{f['tipo']}] {f['nombre']} — {estado_b}")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean_alias(s):
    if not s: return ''
    return str(s).strip().upper().lstrip('@').replace('\xa0', '').replace('  ', ' ')

def find_apostador_id(nombre_excel, alias_excel):
    alias_c = clean_alias(alias_excel)
    nombre_c = nombre_excel.upper().strip() if nombre_excel else ''
    for k, v in apostador_to_id.items():
        if k.upper().lstrip('@') == alias_c:
            return v
    for k, v in apostador_to_id.items():
        if alias_c and (alias_c in k.upper() or k.upper() in alias_c):
            return v
    return None

def to_int(v):
    try:
        return int(v) if v is not None else None
    except:
        return None

# ── Leer Excel ────────────────────────────────────────────────────────────────
print("\nLeyendo Excel (hoja '50- TBL MASTER', fase '30- OCTAVOS')...")
wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
ws = wb['50- TBL MASTER']

# Estructura columnas (verificada sesion 60):
# col[1]=ID PARTIDO, col[8]=NOMBRE, col[9]=ALIAS
# col[12]=pred_local, col[14]=pred_visitante
# col[24]=J-AMARILLAS, col[25]=K-ROJAS, col[26]=L-VAR, col[27]=M-PENALES
# col[28]=N-1ER GOL, col[29]=O-TANDA EQ1, col[30]=O-TANDA EQ2, col[31]=QUIEN CLASIFICA

preds = []
unmatched = {}
partidos_sin_match = set()
sin_preds = []

for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:
        continue  # header
    if row[6] != '30- OCTAVOS':
        continue

    pid_str = str(row[1]).strip() if row[1] else ''
    nombre  = str(row[8]).strip() if row[8] else ''
    alias   = str(row[9]) if row[9] else ''

    uid = find_apostador_id(nombre, alias)
    if not uid:
        key = clean_alias(alias) or nombre.upper()
        unmatched[key] = unmatched.get(key, 0) + 1
        continue

    partido_db = partidos_8vos.get(pid_str)
    if not partido_db:
        partidos_sin_match.add(pid_str)
        continue

    pred_l = to_int(row[12])
    pred_v = to_int(row[14])

    if pred_l is None and pred_v is None:
        sin_preds.append((clean_alias(alias), pid_str))
        continue

    # Tanda: None si no hay predicción; valores 2-6 son tandas reales
    tanda_l = to_int(row[29])
    tanda_v = to_int(row[30])

    # Quien clasifica → equipo_id
    clasifica_nombre = str(row[31]).strip() if row[31] else None
    clasifica_id = find_equipo_id(clasifica_nombre) if clasifica_nombre else None

    preds.append({
        'apostador_id':                 uid,
        'partido_id':                   partido_db['id'],
        'pred_local':                   pred_l if pred_l is not None else 0,
        'pred_visitante':               pred_v if pred_v is not None else 0,
        'pred_amarillas':               to_int(row[24]),
        'pred_rojas':                   to_int(row[25]),
        'pred_var':                     to_int(row[26]),
        'pred_penales_partido':         to_int(row[27]),
        'pred_minuto_gol':              to_int(row[28]),
        'pred_penales_local_tanda':     tanda_l,
        'pred_penales_visitante_tanda': tanda_v,
        'pred_equipo_clasifica':        clasifica_id,
        '_alias':                       clean_alias(alias),
        '_partido':                     pid_str,
    })

print(f"Pronosticos resueltos: {len(preds)}")
print(f"Sin prediccion (skipped): {len(sin_preds)}")

if unmatched:
    print(f"Aliases sin match ({len(unmatched)}): {list(unmatched.keys())}")
else:
    print("Aliases sin match: ninguno ✅")

if partidos_sin_match:
    print(f"Partidos no encontrados en BD: {sorted(partidos_sin_match)}")

if sin_preds:
    print(f"Sin preds (None/None): {sin_preds}")

# ── Muestra dry-run ───────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"RESUMEN: {len(preds)} apuestas × {len(partidos_8vos)} partidos")
print(f"  R32 fases a bloquear: {len(fases_r32)}")

if not DO_IMPORT:
    print("\n[DRY RUN] Primeras 10 apuestas que se importarian:")
    for p in preds[:10]:
        alias_bd = next((u['username'] for u in bd_apostadores if u['id'] == p['apostador_id']), str(p['apostador_id']))
        print(f"  {alias_bd:<22} {p['_partido']}  {p['pred_local']}-{p['pred_visitante']}"
              f"  J={p['pred_amarillas']} K={p['pred_rojas']} L={p['pred_var']}"
              f"  M={p['pred_penales_partido']} N={p['pred_minuto_gol']}"
              f"  TL={p['pred_penales_local_tanda']} TV={p['pred_penales_visitante_tanda']}"
              f"  Cls={p['pred_equipo_clasifica']}")
    print(f"\nTotal a importar: {len(preds)} apuestas")
    print("Para importar y bloquear R32: run_importar_8vos.bat --import")
    sys.exit(0)

# ── IMPORTAR ──────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("BLOQUEAR FASE R32...")
for fila in fases_r32:
    if not fila['bloqueada']:
        cur_bec.execute("UPDATE fase SET bloqueada = TRUE WHERE id = %s", (fila['id'],))
        print(f"  ✅ Fase id={fila['id']} [{fila['nombre']}] BLOQUEADA")
    else:
        print(f"  ⏭ Fase id={fila['id']} [{fila['nombre']}] ya estaba bloqueada")

print(f"\nIMPORTANDO {len(preds)} pronosticos 8vos...")
upserted = 0
errors = 0

for pred in preds:
    try:
        cur_bec.execute("""
            INSERT INTO apuesta (
                apostador_id, partido_id,
                pred_local, pred_visitante,
                pred_amarillas, pred_rojas, pred_var,
                pred_penales_partido, pred_minuto_gol,
                pred_penales_local_tanda, pred_penales_visitante_tanda,
                pred_equipo_clasifica
            ) VALUES (
                %(apostador_id)s, %(partido_id)s,
                %(pred_local)s, %(pred_visitante)s,
                %(pred_amarillas)s, %(pred_rojas)s, %(pred_var)s,
                %(pred_penales_partido)s, %(pred_minuto_gol)s,
                %(pred_penales_local_tanda)s, %(pred_penales_visitante_tanda)s,
                %(pred_equipo_clasifica)s
            )
            ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                pred_local                   = EXCLUDED.pred_local,
                pred_visitante               = EXCLUDED.pred_visitante,
                pred_amarillas               = EXCLUDED.pred_amarillas,
                pred_rojas                   = EXCLUDED.pred_rojas,
                pred_var                     = EXCLUDED.pred_var,
                pred_penales_partido         = EXCLUDED.pred_penales_partido,
                pred_minuto_gol              = EXCLUDED.pred_minuto_gol,
                pred_penales_local_tanda     = EXCLUDED.pred_penales_local_tanda,
                pred_penales_visitante_tanda = EXCLUDED.pred_penales_visitante_tanda,
                pred_equipo_clasifica        = EXCLUDED.pred_equipo_clasifica
        """, pred)
        upserted += 1
    except Exception as e:
        errors += 1
        alias = pred.get('_alias', '?')
        pid   = pred.get('_partido', '?')
        print(f"  ERROR {alias} {pid}: {e}")
        conn_bec.rollback()

conn_bec.commit()
print(f"\n✅ Importados: {upserted}")
if errors:
    print(f"❌ Errores: {errors}")

# ── Verificación final ────────────────────────────────────────────────────────
cur_bec.execute("""
    SELECT COUNT(*) AS total, COUNT(DISTINCT a.apostador_id) AS apostadores,
           COUNT(DISTINCT a.partido_id) AS partidos
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    WHERE p.numero_fifa BETWEEN 89 AND 96
""")
v = cur_bec.fetchone()
print(f"\nVerificacion BD 8vos:")
print(f"  Total apuestas: {v['total']} ({v['apostadores']} apostadores × {v['partidos']} partidos)")

# Verificar bloqueo R32
cur_bec.execute("""
    SELECT nombre, bloqueada FROM fase
    WHERE torneo_id = %s AND tipo ILIKE 'ronda32'
    ORDER BY id
""", (TORNEO_ID,))
fases_check = cur_bec.fetchall()
print("\nEstado fases R32:")
for f in fases_check:
    estado = '✅ BLOQUEADA' if f['bloqueada'] else '❌ NO BLOQUEADA'
    print(f"  {f['nombre']}: {estado}")

print("\n✅ Listo. Ahora ejecutar: POST /calcular-puntajes/2")
print("   (el endpoint auto-bloquea grupos completos y calcula 8vos)")

conn_bec.close()
conn_app.close()
