# -*- coding: utf-8 -*-
"""
recalc_octavos_bloquear_cuartos.py
1) Recalcula puntajes del torneo (POST /calcular-puntajes/2) -> recomputa octavos
   con las predicciones actuales (ya corregido el swap sanbie/pato).
2) Bloquea la fase de CUARTOS (fase.bloqueada=TRUE) para cerrar la carga de apuestas.

Uso:
  backend\.venv\Scripts\python.exe recalc_octavos_bloquear_cuartos.py
"""
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

API_BASE = "http://localhost:8000/api/v1"
API_USER, API_PASS = "jose", "catalina"
TORNEO_ID = 2
CONN_BEC = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"

# ── 1. Recalcular puntajes vía API ────────────────────────────────────────────
print("== 1) Recalculando puntajes (POST /calcular-puntajes/2) ==")
try:
    lr = requests.post(f"{API_BASE}/auth/login", json={"username": API_USER, "password": API_PASS}, timeout=30)
    tok = lr.json().get("access_token", "")
except Exception as e:
    sys.exit(f"ERROR login (uvicorn corriendo en :8000?): {e}")
if not tok:
    sys.exit(f"ERROR: login sin token -> {lr.status_code} {lr.text[:200]}")

hdr = {"Authorization": f"Bearer {tok}"}
try:
    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}", headers=hdr, timeout=300)
    cd = cr.json()
except Exception as e:
    sys.exit(f"ERROR recalculo: {e}")

if cd.get("ok"):
    print(f"  OK plenos={cd.get('plenos')} aciertos={cd.get('aciertos')} fallos={cd.get('fallos')}")
    for fase, d in (cd.get("por_fase") or {}).items():
        print(f"    {fase}: {d}")
    r16 = cd.get("ronda16") or {}
    if r16:
        print(f"    ronda16: {r16}")
    print(f"  globales_procesadas={cd.get('globales_procesadas')}")
else:
    print(f"  RESPUESTA: {cd}")

# ── 2. Bloquear fase de cuartos ───────────────────────────────────────────────
print("\n== 2) Bloqueando fase de CUARTOS ==")
conn = psycopg2.connect(CONN_BEC)
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
    FROM fase
    WHERE torneo_id = %s
      AND (tipo ILIKE 'cuartos' OR tipo ILIKE '%%cuarto%%' OR nombre ILIKE '%%cuarto%%')
    ORDER BY id
""", (TORNEO_ID,))
fases = cur.fetchall()
if not fases:
    print("  No se encontro fase de cuartos (revisar tipo/nombre en tabla fase).")
    cur.execute("SELECT id, nombre, tipo FROM fase WHERE torneo_id=%s ORDER BY id", (TORNEO_ID,))
    print("  Fases del torneo:", [(f['id'], f['tipo'], f['nombre']) for f in cur.fetchall()])
else:
    for f in fases:
        if f['bloqueada']:
            print(f"  id={f['id']} [{f['tipo']}] {f['nombre']} -> ya estaba BLOQUEADA")
        else:
            cur.execute("UPDATE fase SET bloqueada=TRUE WHERE id=%s", (f['id'],))
            print(f"  id={f['id']} [{f['tipo']}] {f['nombre']} -> BLOQUEADA ahora")

conn.close()
print("\nListo.")
