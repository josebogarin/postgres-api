"""Diagnostico: muestra columnas de apuesta y partidos de torneo_id=2"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = _osp.path.join(_BASE, 'resultado_diag_apuesta.txt')
lines = []

try:
    conn = psycopg2.connect(**DB)
    conn.autocommit = True
    cur = conn.cursor()

    # Columnas de apuesta
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'apuesta'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    lines.append("Columnas apuesta:")
    for c in cols:
        lines.append(f"  {c[0]:35s} {c[1]}")

    # Partidos del torneo 2 (Copa Mundial)
    cur.execute("""
        SELECT p.id,
               COALESCE(el.nombre_es, el.nombre) AS local,
               COALESCE(ev.nombre_es, ev.nombre) AS visitante,
               f.nombre as fase
        FROM partido p
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2
        ORDER BY p.id
        LIMIT 10;
    """)
    rows = cur.fetchall()
    lines.append(f"\nPrimeros 10 partidos torneo_id=2:")
    for r in rows:
        lines.append(f"  id={r[0]}  {r[1]} vs {r[2]}  fase={r[3]}")

    cur.execute("""
        SELECT COUNT(*) FROM partido p
        JOIN fase f ON f.id = p.fase_id WHERE f.torneo_id = 2;
    """)
    lines.append(f"Total partidos torneo 2: {cur.fetchone()[0]}")

    # Muestra apuestas con sus columnas clave
    cur.execute("SELECT * FROM apuesta LIMIT 1;")
    desc = [d[0] for d in cur.description]
    lines.append(f"\nCampos reales de apuesta: {desc}")

    # Nombres distintos de apostadores en apuesta (para match con pronosticos_aux)
    cur.execute("SELECT DISTINCT nombre_apostador FROM apuesta WHERE nombre_apostador IS NOT NULL LIMIT 10;")
    lines.append("\nNombres en apuesta.nombre_apostador:")
    for r in cur.fetchall():
        lines.append(f"  {r[0]}")

    # Nombres distintos en pronosticos_aux
    cur.execute("SELECT DISTINCT nombre FROM pronosticos_aux LIMIT 10;")
    lines.append("\nNombres en pronosticos_aux.nombre:")
    for r in cur.fetchall():
        lines.append(f"  {r[0]}")

    cur.close()
    conn.close()
except Exception as e:
    import traceback
    lines.append(f"ERROR: {e}\n{traceback.format_exc()}")

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("OK")
