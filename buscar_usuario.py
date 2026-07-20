import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import psycopg2, psycopg2.extras

PG_APP = dict(host="localhost", port=5432, user="app_user",
              password="superpassword", dbname="app_db")

terminos = sys.argv[1:] if len(sys.argv) > 1 else ["gonzalo", "gimenez", "giménez"]

with psycopg2.connect(**PG_APP, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
    with conn.cursor() as cur:
        print("=== Todos los apostadores (id, username, nombre) ===")
        cur.execute("SELECT id, username, nombre FROM users ORDER BY id")
        rows = cur.fetchall()
        for r in rows:
            nombre = (r["nombre"] or "").lower()
            username = (r["username"] or "").lower()
            # Mostrar todos, o filtrar por terminos
            match = any(t.lower() in nombre or t.lower() in username for t in terminos)
            if match or "--all" in sys.argv:
                print(f"  id={r['id']:>3}  username={r['username']:<20}  nombre={r['nombre']}")
