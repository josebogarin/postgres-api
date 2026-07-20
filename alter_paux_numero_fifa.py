"""
Agrega columna numero_partido_fifa INTEGER a pronosticos_aux
e infiere el valor desde id_partido (P001 -> 1, P072 -> 72).
"""
import psycopg2, os

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = os.path.join(os.path.dirname(__file__), "resultado_alter_paux.txt")

lines = []
try:
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Agregar columna
    cur.execute("ALTER TABLE pronosticos_aux ADD COLUMN IF NOT EXISTS numero_partido_fifa INTEGER;")
    lines.append("ALTER TABLE OK — columna numero_partido_fifa agregada")

    # 2. Poblar desde id_partido (P001 -> 1, P072 -> 72)
    cur.execute("""
        UPDATE pronosticos_aux
        SET numero_partido_fifa = CAST(SUBSTRING(id_partido FROM 2) AS INTEGER)
        WHERE numero_partido_fifa IS NULL;
    """)
    lines.append(f"UPDATE OK — {cur.rowcount} filas actualizadas")

    # 3. Verificacion
    cur.execute("""
        SELECT numero_partido_fifa, id_partido, COUNT(*)
        FROM pronosticos_aux
        GROUP BY numero_partido_fifa, id_partido
        ORDER BY numero_partido_fifa
        LIMIT 5
    """)
    lines.append("Muestra (num_fifa, id_partido, registros):")
    for row in cur.fetchall():
        lines.append(f"  {row}")

    cur.execute("SELECT MIN(numero_partido_fifa), MAX(numero_partido_fifa) FROM pronosticos_aux;")
    mn, mx = cur.fetchone()
    lines.append(f"Rango: {mn} -> {mx}")

    cur.close()
    conn.close()
except Exception as e:
    lines.append(f"ERROR: {e}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("\n".join(lines))
