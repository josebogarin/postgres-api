"""
actualizar_r32_desde_excel.py
=====================================
Lee la hoja "40- RESULTADOS OFICIALES" del Excel TBL CHECK y actualiza
los partidos R32 (P073-P088) en la BD con los valores oficiales.
Solo actualiza partidos que tienen datos (no PENDIENTE).

Ejecutar:
  cd "C:\proyecto FAST API"
  backend\.venv\Scripts\python.exe actualizar_r32_desde_excel.py
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))

import sys, pathlib, openpyxl, psycopg2, requests

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "dbname": "becbuc", "user": "app_user", "password": "superpassword",
}
API_BASE  = "http://localhost:8000/api/v1"
API_USER  = "jose"
API_PASS  = "catalina"
TORNEO_ID = 2

EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else None
if not EXCEL_PATH:
    # Buscar en ubicaciones conocidas
    search_dirs = [
        r"C:\Users\Jose Bogarin\Downloads",
        r"C:\Users\Jose Bogarin\Desktop",
        _BASE,
        _osp.path.join(_BASE, 'documentacion'),
    ]
    # También buscar en uploads de las sesiones activas (solo nivel 1)
    uploads_base = pathlib.Path(r"C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions")
    if uploads_base.exists():
        for session_dir in uploads_base.iterdir():
            if not session_dir.is_dir():
                continue
            for sub_dir in session_dir.iterdir():
                uploads_path = sub_dir / "local_9db4502a-7e61-4142-bb4b-38eee8035736" / "uploads"
                if uploads_path.exists():
                    search_dirs.append(str(uploads_path))
                    break

    for d in search_dirs:
        p = pathlib.Path(d)
        if not p.exists():
            continue
        matches = list(p.glob("*TBL CHECK*.xlsx")) + list(p.glob("20260702*.xlsx"))
        if matches:
            EXCEL_PATH = str(matches[0])
            break

    if not EXCEL_PATH:
        sys.exit("❌ No se encontró el Excel.\n   Ejecutá: backend\\.venv\\Scripts\\python.exe actualizar_r32_desde_excel.py \"C:\\ruta\\al\\archivo.xlsx\"")

print(f"📂 Excel: {EXCEL_PATH}")

wb  = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws  = wb["40- RESULTADOS OFICIALES"]

def iv(v, none_if=None):
    """int o None; trata 'none_if' como None (ej: 99 = sin tanda)."""
    try:
        x = int(v) if v is not None else None
        if none_if is not None and x == none_if:
            return None
        return x
    except:
        return None

excel_r32 = {}
for row in ws.iter_rows(min_row=2, values_only=True):
    pid = row[0]
    if not pid or not str(pid).startswith('P'):
        continue
    nf = int(str(pid)[1:])
    if not (73 <= nf <= 88):
        continue
    estado_excel = str(row[37]).strip().upper() if row[37] else ''
    if estado_excel == 'PENDIENTE' or row[11] is None:
        continue  # skip partidos sin resultado
    excel_r32[nf] = {
        "goles_local":             iv(row[11]),
        "goles_visitante":         iv(row[13]),
        "amarillas":               iv(row[29]),
        "rojas":                   iv(row[30]),
        "decisiones_var":          iv(row[31]),
        "penales_partido":         iv(row[32]),
        "minuto_primer_gol":       iv(row[33]),
        "penales_local_tanda":     iv(row[34], none_if=99),   # 99 = sin tanda
        "penales_visitante_tanda": iv(row[35], none_if=99),
    }

print(f"✅ Excel R32 leído: {len(excel_r32)} partidos con resultado")
for nf, d in sorted(excel_r32.items()):
    tanda = f" (tanda {d['penales_local_tanda']}-{d['penales_visitante_tanda']})" if d['penales_local_tanda'] is not None else ""
    print(f"  P{nf:03d}: {d['goles_local']}-{d['goles_visitante']}{tanda} | amar={d['amarillas']} rojas={d['rojas']} var={d['decisiones_var']} penP={d['penales_partido']} min={d['minuto_primer_gol']}")

# ── 2. Leer partidos R32 de BD ────────────────────────────────────────────────
conn = psycopg2.connect(**DB_CONFIG)
cur  = conn.cursor()

cur.execute("""
    SELECT p.id, p.numero_fifa,
           p.goles_local, p.goles_visitante,
           p.amarillas, p.rojas, p.decisiones_var,
           p.penales_partido, p.minuto_primer_gol,
           p.penales_local, p.penales_visitante,
           p.estado
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = %s AND p.numero_fifa BETWEEN 73 AND 88
    ORDER BY p.numero_fifa
""", (TORNEO_ID,))

bd_r32 = {}
for row in cur.fetchall():
    pid_db, nf, gl, gv, amar, rojas, var_, pen, min_g, tl, tv, estado = row
    bd_r32[nf] = {
        "id": pid_db, "estado": estado,
        "goles_local": gl, "goles_visitante": gv,
        "amarillas": amar, "rojas": rojas, "decisiones_var": var_,
        "penales_partido": pen, "minuto_primer_gol": min_g,
        "penales_local_tanda": tl, "penales_visitante_tanda": tv,
    }

print(f"\n✅ BD R32 leída: {len(bd_r32)} partidos")

# ── 3. Comparar y actualizar ──────────────────────────────────────────────────
# Mapeo: clave interna → nombre real en tabla partido
CAMPO_MAP = {
    "goles_local":             "goles_local",
    "goles_visitante":         "goles_visitante",
    "amarillas":               "amarillas",
    "rojas":                   "rojas",
    "decisiones_var":          "decisiones_var",
    "penales_partido":         "penales_partido",
    "minuto_primer_gol":       "minuto_primer_gol",
    "penales_local_tanda":     "penales_local",     # columna real en BD
    "penales_visitante_tanda": "penales_visitante", # columna real en BD
}
campos = list(CAMPO_MAP.keys())

actualizados = 0
sin_cambios  = 0
diffs_log    = []

for nf, ex in sorted(excel_r32.items()):
    bd = bd_r32.get(nf)
    if not bd:
        print(f"  ⚠️  P{nf:03d} no encontrado en BD")
        continue

    # updates: {col_real_bd: valor}
    updates = {}
    for campo in campos:
        ex_val = ex.get(campo)
        bd_val = bd.get(campo)
        if ex_val is None:
            continue  # sin dato en Excel, no tocar
        if ex_val != bd_val:
            col_bd = CAMPO_MAP[campo]
            updates[col_bd] = ex_val
            diffs_log.append(f"  P{nf:03d} {campo}: BD={bd_val} → Excel={ex_val}")

    # Marcar como finalizado si tiene goles
    if ex.get("goles_local") is not None and bd.get("estado") != "finalizado":
        updates["estado"] = "finalizado"
        diffs_log.append(f"  P{nf:03d} estado: {bd['estado']} → finalizado")

    if not updates:
        sin_cambios += 1
        continue

    set_clauses = ", ".join(f"{col} = %s" for col in updates)
    vals = list(updates.values()) + [bd["id"]]
    cur.execute(f"UPDATE partido SET {set_clauses} WHERE id = %s", vals)
    actualizados += 1

conn.commit()
cur.close()
conn.close()

print(f"\n📊 Resultado:")
print(f"  Partidos actualizados: {actualizados}")
print(f"  Sin cambios:           {sin_cambios}")

if diffs_log:
    print(f"\n📝 Cambios aplicados ({len(diffs_log)}):")
    for d in diffs_log:
        print(d)

if actualizados == 0:
    print("\n✅ La BD R32 ya estaba sincronizada con el Excel.")
    sys.exit(0)

# ── 4. Recalcular puntajes ────────────────────────────────────────────────────
print("\n⚙️  Recalculando puntajes (puede tardar ~60s)...")
login_r = requests.post(f"{API_BASE}/auth/login",
                        json={"username": API_USER, "password": API_PASS})
tok = login_r.json().get("access_token", "")
if not tok:
    print("❌ No se pudo obtener token. Recalculá manualmente: POST /calcular-puntajes/2")
    sys.exit(1)

headers = {"Authorization": f"Bearer {tok}"}
calc_r  = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}",
                        headers=headers, timeout=300)
calc_d  = calc_r.json()
if calc_d.get("ok"):
    g = calc_d.get('grupos', {})
    r32 = calc_d.get('ronda32', {})
    print(f"✅ Puntajes recalculados:")
    print(f"   plenos={calc_d['plenos']} aciertos={calc_d['aciertos']}")
    print(f"   grupos total={g.get('total',0)} | ronda32 total={r32.get('total',0)}")
else:
    print(f"⚠️  Recálculo: {calc_d}")
