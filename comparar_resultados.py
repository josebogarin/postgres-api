"""
Compara los resultados del Excel 20260623-check.xlsx contra la BD becbuc.
Detecta diferencias partido a partido en: goles, amarillas, rojas, VAR,
penales del partido (M), minuto primer gol (N).

Ejecutar:
    python comparar_resultados.py
"""

import psycopg2
import openpyxl
import os
from datetime import datetime

# ── Configuracion ────────────────────────────────────────────────────────────
DB   = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
XLSX = r"C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\local_2cded1ed-1658-4b6a-8527-0fe1e6eff1cc\uploads\20260623-check.xlsx"
OUT  = r"C:\proyecto FAST API\comparacion_resultados.txt"

# ── Leer Excel ───────────────────────────────────────────────────────────────
wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb.active

excel = {}
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0:
        continue
    pid = row[0]
    if not pid or not str(pid).startswith("P"):
        continue
    estado = row[29]
    if estado != "FINALIZADO":
        continue
    # Extraer numero limpio: P001 -> 1
    try:
        num = int(str(pid).replace("P", "").lstrip("0") or "0")
    except ValueError:
        num = 0
    excel[num] = {
        "pid_str"  : pid,
        "eq1"      : str(row[9]).strip().upper() if row[9] else "",
        "goles1"   : row[11],
        "goles2"   : row[13],
        "eq2"      : str(row[14]).strip().upper() if row[14] else "",
        "amarillas": row[22],
        "rojas"    : row[23],
        "var"      : row[24],
        "pen_m"    : row[25],
        "minuto"   : row[26],
    }

# ── Leer BD ──────────────────────────────────────────────────────────────────
conn = psycopg2.connect(**DB)
cur  = conn.cursor()

cur.execute("""
    SELECT
        p.numero_fifa,
        COALESCE(el.nombre_es, el.nombre) AS equipo_local,
        p.goles_local,
        p.goles_visitante,
        COALESCE(ev.nombre_es, ev.nombre) AS equipo_visitante,
        COALESCE(p.amarillas, 0)           AS amarillas,
        COALESCE(p.rojas, 0)               AS rojas,
        COALESCE(p.decisiones_var, 0)      AS var,
        COALESCE(p.penales_partido, 0)     AS pen_m,
        p.minuto_primer_gol                AS minuto,
        p.estado
    FROM partido p
    JOIN equipo el ON p.equipo_local_id    = el.id
    JOIN equipo ev ON p.equipo_visitante_id = ev.id
    JOIN fase f    ON p.fase_id            = f.id
    WHERE f.torneo_id = 2
      AND p.estado IN ('finalizado', 'en_juego')
    ORDER BY p.numero_fifa
""")

bd = {}
for row in cur.fetchall():
    num = row[0]
    bd[num] = {
        "eq1"      : str(row[1]).strip().upper(),
        "goles1"   : row[2],
        "goles2"   : row[3],
        "eq2"      : str(row[4]).strip().upper(),
        "amarillas": row[5],
        "rojas"    : row[6],
        "var"      : row[7],
        "pen_m"    : row[8],
        "minuto"   : row[9],
        "estado"   : row[10],
    }

cur.close()
conn.close()

# ── Comparar ─────────────────────────────────────────────────────────────────
CAMPOS = [
    ("goles1",    "Goles local"),
    ("goles2",    "Goles visit."),
    ("amarillas", "Amarillas (J)"),
    ("rojas",     "Rojas (K)"),
    ("var",       "VAR (L)"),
    ("pen_m",     "Pen.partido (M)"),
    ("minuto",    "Minuto gol (N)"),
]

iguales    = []
diferencias = []
solo_excel = []
solo_bd    = []

todos_nums = sorted(set(list(excel.keys()) + list(bd.keys())))

for num in todos_nums:
    e = excel.get(num)
    b = bd.get(num)

    if e and not b:
        solo_excel.append(num)
        continue
    if b and not e:
        solo_bd.append(num)
        continue

    diffs = []
    for campo, label in CAMPOS:
        ve = e[campo] if e[campo] is not None else 0
        vb = b[campo] if b[campo] is not None else 0
        # Convertir a int para comparar
        try:
            ve = int(ve)
            vb = int(vb)
        except (TypeError, ValueError):
            pass
        # Caso especial: minuto_gol 99 en Excel = sin gol = NULL/0 en BD
        if campo == "minuto" and ve == 99 and vb == 0:
            continue
        if ve != vb:
            diffs.append((label, ve, vb))

    entry = {
        "num"  : num,
        "pid"  : e["pid_str"],
        "eq1"  : e["eq1"],
        "eq2"  : e["eq2"],
        "diffs": diffs,
    }
    if diffs:
        diferencias.append(entry)
    else:
        iguales.append(entry)

# ── Generar reporte ──────────────────────────────────────────────────────────
lines = []
ts = datetime.now().strftime("%Y-%m-%d %H:%M")
lines.append(f"COMPARACION EXCEL vs BD BECBUC  —  {ts}")
lines.append("=" * 70)
lines.append(f"Partidos FINALIZADOS en Excel : {len(excel)}")
lines.append(f"Partidos finalizados en BD    : {len(bd)}")
lines.append(f"Partidos iguales              : {len(iguales)}")
lines.append(f"Partidos con diferencias      : {len(diferencias)}")
lines.append(f"Solo en Excel (no en BD)      : {len(solo_excel)}")
lines.append(f"Solo en BD   (no en Excel)    : {len(solo_bd)}")
lines.append("")

if diferencias:
    lines.append("━" * 70)
    lines.append("DIFERENCIAS ENCONTRADAS")
    lines.append("━" * 70)
    for d in diferencias:
        lines.append(f"\n  {d['pid']}  {d['eq1']} vs {d['eq2']}")
        for label, ve, vb in d["diffs"]:
            lines.append(f"    {label:<20}  Excel={ve}   BD={vb}   ← DIFERENCIA")
else:
    lines.append("✅ TODOS LOS PARTIDOS COINCIDEN — No hay diferencias.")

if solo_excel:
    lines.append("")
    lines.append("━" * 70)
    lines.append("PARTIDOS EN EXCEL PERO NO EN BD (no finalizados en BD):")
    for num in solo_excel:
        e = excel[num]
        lines.append(f"  {e['pid_str']}  {e['eq1']} {e['goles1']}-{e['goles2']} {e['eq2']}")

if solo_bd:
    lines.append("")
    lines.append("━" * 70)
    lines.append("PARTIDOS EN BD PERO NO EN EXCEL (no marcados FINALIZADO en Excel):")
    for num in solo_bd:
        b2 = bd[num]
        lines.append(f"  P{str(num).zfill(3)}  {b2['eq1']} {b2['goles1']}-{b2['goles2']} {b2['eq2']}  [{b2['estado']}]")

lines.append("")
lines.append("=" * 70)
lines.append("FIN DEL REPORTE")

report = "\n".join(lines)
print(report)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\nReporte guardado en: {OUT}")
