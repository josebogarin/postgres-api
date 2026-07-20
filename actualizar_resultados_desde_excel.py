"""
actualizar_resultados_desde_excel.py
=====================================
Lee la hoja "40- RESULTADOS OFICIALES" del Excel TBL CHECK y actualiza
todos los partidos en la BD con los valores oficiales.

Ejecutar con el uvicorn activo:
  cd "C:\proyecto FAST API"
  backend\.venv\Scripts\python.exe actualizar_resultados_desde_excel.py

O pasar ruta al Excel como argumento:
  backend\.venv\Scripts\python.exe actualizar_resultados_desde_excel.py "ruta\al\archivo.xlsx"
"""

import sys
import pathlib
import openpyxl
import psycopg2
import requests
import json

# ── Configuración ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "becbuc",
    "user": "app_user",
    "password": "superpassword",
}
API_BASE  = "http://localhost:8000/api/v1"
API_USER  = "jose"
API_PASS  = "catalina"
TORNEO_ID = 2

# Ruta al Excel (arg opcional, si no se pasa busca en uploads/)
EXCEL_PATH = sys.argv[1] if len(sys.argv) > 1 else None
if not EXCEL_PATH:
    # Buscar en la carpeta típica de uploads de Cowork
    candidates = list(pathlib.Path(r"C:\Users\Jose Bogarin\AppData\Roaming\Claude")
                       .rglob("20260702- TBL CHECK PARA JOSE.xlsx"))
    if candidates:
        EXCEL_PATH = str(candidates[0])
    else:
        sys.exit("❌ No se encontró el Excel. Pasá la ruta como argumento.")

print(f"📂 Excel: {EXCEL_PATH}")

# ── 1. Leer Excel ─────────────────────────────────────────────────────────────
wb   = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
ws   = wb["40- RESULTADOS OFICIALES"]

excel_stats = {}   # {numero_fifa: {...}}
for row in ws.iter_rows(min_row=2, values_only=True):
    pid = row[0]
    if not pid or not str(pid).startswith('P'):
        continue
    nf = int(str(pid)[1:])
    def iv(v):   # int or None
        try: return int(v) if v is not None else None
        except: return None

    excel_stats[nf] = {
        "goles_local":             iv(row[11]),   # col12
        "goles_visitante":         iv(row[13]),   # col14
        "amarillas":               iv(row[29]),   # col30
        "rojas":                   iv(row[30]),   # col31
        "decisiones_var":          iv(row[31]),   # col32
        "penales_partido":         iv(row[32]),   # col33
        "minuto_primer_gol":       iv(row[33]),   # col34
        "penales_local_tanda":     iv(row[34]),   # col35
        "penales_visitante_tanda": iv(row[35]),   # col36
    }

print(f"✅ Excel leído: {len(excel_stats)} partidos (P{min(excel_stats)}-P{max(excel_stats)})")

# ── 2. Leer partidos de BD ────────────────────────────────────────────────────
conn = psycopg2.connect(**DB_CONFIG)
cur  = conn.cursor()

cur.execute("""
    SELECT p.id, p.numero_fifa,
           p.goles_local, p.goles_visitante,
           p.amarillas, p.rojas, p.decisiones_var,
           p.penales_partido, p.minuto_primer_gol,
           p.penales_local_tanda, p.penales_visitante_tanda,
           p.estado
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = %s AND p.numero_fifa IS NOT NULL
    ORDER BY p.numero_fifa
""", (TORNEO_ID,))

bd_partidos = {}
for row in cur.fetchall():
    pid_db, nf, gl, gv, amar, rojas, var, pen, min_gol, tl, tv, estado = row
    bd_partidos[nf] = {
        "id": pid_db,
        "goles_local": gl, "goles_visitante": gv,
        "amarillas": amar, "rojas": rojas, "decisiones_var": var,
        "penales_partido": pen, "minuto_primer_gol": min_gol,
        "penales_local_tanda": tl, "penales_visitante_tanda": tv,
        "estado": estado,
    }

print(f"✅ BD leída: {len(bd_partidos)} partidos con numero_fifa")

# ── 3. Comparar y actualizar ──────────────────────────────────────────────────
campos = ["goles_local", "goles_visitante", "amarillas", "rojas", "decisiones_var",
          "penales_partido", "minuto_primer_gol", "penales_local_tanda", "penales_visitante_tanda"]

actualizados = 0
sin_cambios  = 0
sin_bd       = 0
diffs_log    = []

for nf, ex in sorted(excel_stats.items()):
    bd = bd_partidos.get(nf)
    if not bd:
        sin_bd += 1
        continue

    # Solo actualizar partidos finalizados en Excel
    updates = {}
    for campo in campos:
        ex_val = ex.get(campo)
        bd_val = bd.get(campo)
        if ex_val is None:
            continue   # sin datos en Excel, no tocar
        if ex_val != bd_val:
            updates[campo] = ex_val
            diffs_log.append(f"  P{nf:03d} {campo}: BD={bd_val} → Excel={ex_val}")

    if not updates:
        sin_cambios += 1
        continue

    # Construir UPDATE dinámico
    set_clauses = ", ".join(f"{k} = %s" for k in updates)
    vals = list(updates.values()) + [bd["id"]]
    cur.execute(f"UPDATE partido SET {set_clauses} WHERE id = %s", vals)
    actualizados += 1

conn.commit()
cur.close()
conn.close()

print(f"\n📊 Resultado:")
print(f"  Partidos actualizados: {actualizados}")
print(f"  Sin cambios:           {sin_cambios}")
print(f"  Sin BD (KO pendiente): {sin_bd}")

if diffs_log:
    print(f"\n📝 Cambios aplicados ({len(diffs_log)}):")
    for d in diffs_log:
        print(d)

if actualizados == 0:
    print("\n✅ La BD ya estaba sincronizada con el Excel.")
    sys.exit(0)

# ── 4. Recalcular puntajes ────────────────────────────────────────────────────
print("\n⚙️  Recalculando puntajes...")
login_r = requests.post(f"{API_BASE}/auth/login",
                        json={"username": API_USER, "password": API_PASS})
tok = login_r.json().get("access_token", "")
if not tok:
    print("❌ No se pudo obtener token. Recalculá manualmente: POST /calcular-puntajes/2?force_grupos=true")
    sys.exit(1)

headers = {"Authorization": f"Bearer {tok}"}
calc_r  = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}?force_grupos=true",
                        headers=headers, timeout=300)
calc_d  = calc_r.json()
if calc_d.get("ok"):
    print(f"✅ Puntajes recalculados: plenos={calc_d['plenos']} aciertos={calc_d['aciertos']}")
else:
    print(f"⚠️  Recálculo: {calc_d}")
