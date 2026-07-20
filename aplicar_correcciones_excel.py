"""
Aplica las correcciones detectadas en comparar_resultados.py a la BD becbuc.
Fuente de verdad: Excel 20260623-check.xlsx (valores oficiales).

Campos corregidos:
  - decisiones_var   (L)
  - minuto_primer_gol (N) — 99 en Excel = sin gol = NULL en BD
  - amarillas        (J)

Luego recalcula puntajes via POST /calcular-puntajes/2.

Ejecutar:
    & "C:\\proyecto FAST API\\backend\\.venv\\Scripts\\python.exe" "C:\\proyecto FAST API\\aplicar_correcciones_excel.py"
"""

import psycopg2
import urllib.request
import json
from datetime import datetime

DB  = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
API = "http://localhost:8000"

# ── Correcciones detectadas ───────────────────────────────────────────────────
# Formato: (numero_fifa, campo_bd, valor_correcto)
# valor None = NULL en BD (ej. minuto 99 = sin gol)

CORRECCIONES = [
    # --- Minuto primer gol (N) ---
    # P001 MEX vs SUD: Excel=10, BD=9
    (1,  "minuto_primer_gol", 10),
    # P014 ESP vs CAB (0-0): Excel=99 → sin gol → NULL
    (14, "minuto_primer_gol", None),
    # P021 GHA vs PAN: Excel=95, BD=90
    (21, "minuto_primer_gol", 95),
    # P034 ECU vs CUR (0-0): Excel=99 → NULL
    (34, "minuto_primer_gol", None),
    # P039 BEL vs IRN (0-0): Excel=99 → NULL
    (39, "minuto_primer_gol", None),

    # --- VAR (L) ---
    (4,  "decisiones_var", 2),
    (6,  "decisiones_var", 0),
    (7,  "decisiones_var", 0),
    (8,  "decisiones_var", 1),
    (20, "decisiones_var", 2),
    (22, "decisiones_var", 1),
    (26, "decisiones_var", 1),
    (27, "decisiones_var", 2),
    (31, "decisiones_var", 0),
    (37, "decisiones_var", 1),
    (38, "decisiones_var", 1),
    (42, "decisiones_var", 0),
    (43, "decisiones_var", 1),
    (44, "decisiones_var", 1),

    # --- Amarillas (J) ---
    (30, "amarillas", 3),
    (37, "amarillas", 4),
]

# ── Aplicar correcciones ─────────────────────────────────────────────────────
conn = psycopg2.connect(**DB)
cur  = conn.cursor()

print(f"[{datetime.now():%H:%M:%S}] Aplicando {len(CORRECCIONES)} correcciones...\n")

ok  = 0
err = 0

for num_fifa, campo, valor in CORRECCIONES:
    try:
        cur.execute(
            f"UPDATE partido SET {campo} = %s WHERE numero_fifa = %s",
            (valor, num_fifa)
        )
        filas = cur.rowcount
        val_str = str(valor) if valor is not None else "NULL"
        if filas > 0:
            print(f"  ✅ P{str(num_fifa).zfill(3)}  {campo} = {val_str}  ({filas} fila)")
            ok += 1
        else:
            print(f"  ⚠️  P{str(num_fifa).zfill(3)}  {campo} — partido no encontrado (numero_fifa={num_fifa})")
            err += 1
    except Exception as e:
        print(f"  ❌ P{str(num_fifa).zfill(3)}  {campo} — ERROR: {e}")
        err += 1

conn.commit()
cur.close()
conn.close()

print(f"\n[{datetime.now():%H:%M:%S}] Correcciones: {ok} ok, {err} errores.")

# ── Recalcular puntajes ──────────────────────────────────────────────────────
print(f"\n[{datetime.now():%H:%M:%S}] Recalculando puntajes (POST /calcular-puntajes/2)...")

try:
    # Login para obtener token
    login_data = json.dumps({"username": "jose", "password": "catalina"}).encode()
    req = urllib.request.Request(
        f"{API}/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        token = json.loads(resp.read())["access_token"]

    # Recalcular
    req2 = urllib.request.Request(
        f"{API}/api/v1/bets/calcular-puntajes/2",
        data=b"",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req2, timeout=60) as resp2:
        result = json.loads(resp2.read())

    procesados = result.get("procesados", "?")
    plenos     = result.get("plenos", "?")
    aciertos   = result.get("aciertos", "?")
    print(f"  ✅ Puntajes recalculados: {procesados} partidos, {plenos} plenos, {aciertos} aciertos.")

except Exception as e:
    print(f"  ❌ Error al recalcular: {e}")
    print(f"     Ejecutá manualmente: POST {API}/api/v1/bets/calcular-puntajes/2")

print(f"\n[{datetime.now():%H:%M:%S}] Listo.")
