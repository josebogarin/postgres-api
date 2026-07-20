"""
buscar_patito.py
Busca alias en pronosticos_aux para identificar a PATITO.
"""
import sys, io, psycopg2, psycopg2.extras
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

conn = psycopg2.connect(**PG)
cur = conn.cursor()

# Verificar alias en pronosticos_aux
try:
    cur.execute("""
        SELECT DISTINCT alias, nombre
        FROM pronosticos_aux
        ORDER BY alias
    """)
    rows = cur.fetchall()
    print("=== Aliases en pronosticos_aux ===")
    for r in rows:
        print(f"  alias={str(r['alias'] or ''):25s}  nombre={r['nombre']!r}")
except Exception as e:
    print(f"ERROR pronosticos_aux: {e}")

print()

# También buscar en la tabla apuesta si hay algún campo alias
try:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='apuesta'
        ORDER BY ordinal_position
    """)
    cols = [r['column_name'] for r in cur.fetchall()]
    print(f"Columnas en apuesta: {cols}")
except Exception as e:
    print(f"ERROR columns: {e}")

print()

# Buscar en users de app_db para ver si hay un campo apodo/alias
try:
    conn2 = psycopg2.connect(host="localhost", port=5432, user="app_user",
                              password="superpassword", dbname="app_db",
                              cursor_factory=psycopg2.extras.RealDictCursor)
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='users'
        ORDER BY ordinal_position
    """)
    cols2 = [r['column_name'] for r in cur2.fetchall()]
    print(f"Columnas en users (app_db): {cols2}")

    # Mostrar todos los users para ver si hay "patito" en algún campo
    cur2.execute("SELECT * FROM users ORDER BY nombre LIMIT 60")
    users = cur2.fetchall()
    print("\n=== Usuarios en app_db ===")
    for u in users:
        print(f"  id={u.get('id','')} nombre={str(u.get('nombre','') or ''):25s} username={str(u.get('username','') or ''):20s}")
    cur2.close(); conn2.close()
except Exception as e:
    print(f"ERROR app_db: {e}")

cur.close(); conn.close()
