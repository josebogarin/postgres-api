"""
diag_sistema_schema.py
Vuelca el esquema REAL actual de app_db (tabla sistema, users, user_sistemas)
para reconciliar el modelo ORM tras la modernizacion del core.
Salida: diag_sistema_schema.txt
"""
import sys, os

try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet')
    import psycopg2, psycopg2.extras

CONN_APP = "host=localhost port=5432 dbname=app_db user=app_user password=superpassword"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diag_sistema_schema.txt")

lines = []
def log(s=""):
    print(s)
    lines.append(str(s))

try:
    conn = psycopg2.connect(CONN_APP)
except Exception as e:
    log(f"ERROR conexion app_db: {e}")
    log("Docker corriendo? docker start core-postgres")
    open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    sys.exit(1)

cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

for tabla in ("sistema", "users", "user_sistemas"):
    log(f"===== COLUMNAS de {tabla} =====")
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (tabla,))
    rows = cur.fetchall()
    if not rows:
        log(f"  (tabla '{tabla}' NO existe)")
    for r in rows:
        log(f"  {r['column_name']:<28} {r['data_type']:<18} null={r['is_nullable']:<3} def={r['column_default']}")
    log("")

# Contenido de sistema (sin exponer password)
log("===== FILAS en sistema =====")
try:
    cur.execute("SELECT * FROM sistema ORDER BY id")
    for r in cur.fetchall():
        safe = {k: v for k, v in r.items() if 'contrase' not in k.lower() and 'password' not in k.lower()}
        log(f"  {safe}")
except Exception as e:
    log(f"  ERROR: {e}")

conn.close()
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print(f"\nEscrito: {OUT}")
