"""
fix_var_p27_p39.py
Corrige decisiones_var incorrecto en P27 y P39.

Causa: ESPN verify en sesion anterior subio VAR a valores incorrectos.
  P27 Canada vs Qatar    (id=169): ESPN puso 3, correcto es 2
  P39 Belgium vs Iran    (id=180): ESPN puso 2, correcto es 1

Ejecutar:
  cd "C:\proyecto FAST API"
  backend\.venv\Scripts\python.exe fix_var_p27_p39.py
"""
import sys, urllib.request, urllib.error, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import psycopg2
except ImportError:
    print("psycopg2 no disponible - usando API directamente")
    psycopg2 = None

from becbuc_config import BASE_URL, ADMIN_USER, ADMIN_PASS

FIXES = [
    (169, 2, "P27 Canada vs Qatar"),
    (180, 1, "P39 Belgium vs Iran"),
]

def _api(method, url, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def fix_via_psycopg2():
    print("Conectando a PostgreSQL...")
    conn = psycopg2.connect(
        host="localhost", port=5432,
        user="app_user", password="superpassword", dbname="becbuc"
    )
    cur = conn.cursor()
    for partido_id, var_val, label in FIXES:
        cur.execute("UPDATE partido SET decisiones_var = %s WHERE id = %s", (var_val, partido_id))
        cur.execute("SELECT id, decisiones_var FROM partido WHERE id = %s", (partido_id,))
        row = cur.fetchone()
        print(f"  {label} (id={partido_id}): decisiones_var = {row[1]}")
    conn.commit()
    cur.close()
    conn.close()
    print("BD actualizada OK")

if __name__ == "__main__":
    # Paso 1: Corregir VAR
    print("=" * 60)
    print("FIX VAR P27 (Canada vs Qatar) y P39 (Belgium vs Iran)")
    print("=" * 60)

    if psycopg2:
        fix_via_psycopg2()
    else:
        print("ERROR: psycopg2 requerido. Instalar con:")
        print("  backend\\.venv\\Scripts\\pip.exe install psycopg2-binary")
        sys.exit(1)

    # Paso 2: Recalcular puntajes via API
    print("\nRecalculando puntajes...")
    try:
        token = _api("POST", f"{BASE_URL}/api/v1/auth/login",
                     data={"username": ADMIN_USER, "password": ADMIN_PASS})["access_token"]
        result = _api("POST", f"{BASE_URL}/api/v1/bets/calcular-puntajes/2", token=token)
        proc = result.get("partidos_procesados", 0)
        plenos = result.get("plenos", 0)
        aciertos = result.get("aciertos", 0)
        print(f"  OK - {proc} partidos, {plenos} plenos, {aciertos} aciertos")
    except Exception as e:
        print(f"  ERROR en recalculo: {e}")
        print("  Recalcular manualmente desde Herramientas en el portal")

    print("\nLISTO.")
