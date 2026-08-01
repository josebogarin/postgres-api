"""Verifica que pronosticos_aux y apuesta tienen el mismo contenido."""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = _osp.path.join(_BASE, 'resultado_verificar_sync.txt')
lines = []

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Totales en cada tabla
cur.execute("SELECT COUNT(*) FROM pronosticos_aux;")
lines.append(f"pronosticos_aux total filas: {cur.fetchone()[0]}")

cur.execute("""
    SELECT COUNT(*) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    WHERE f.torneo_id = 2;
""")
lines.append(f"apuesta torneo 2 total filas: {cur.fetchone()[0]}")

# Comparacion campo a campo: filas donde los valores DIFIEREN
cur.execute("""
    SELECT COUNT(*) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    JOIN pronosticos_aux pa ON pa.numero_partido_fifa = a.numero_fifa
                           AND LOWER(pa.nombre) = LOWER(a.nombre_apostador)
    WHERE f.torneo_id = 2
      AND (
          a.pred_local        IS DISTINCT FROM pa.goles_local     OR
          a.pred_visitante    IS DISTINCT FROM pa.goles_visitante  OR
          a.pred_amarillas    IS DISTINCT FROM pa.amarillas        OR
          a.pred_rojas        IS DISTINCT FROM pa.rojas            OR
          a.pred_var          IS DISTINCT FROM pa.var              OR
          a.pred_penales_partido IS DISTINCT FROM pa.penales       OR
          a.pred_minuto_gol   IS DISTINCT FROM pa.primer_gol
      );
""")
diferencias = cur.fetchone()[0]
lines.append(f"Filas con diferencias: {diferencias}")

# Filas sin par (apuesta sin match en pronosticos_aux)
cur.execute("""
    SELECT COUNT(*) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    LEFT JOIN pronosticos_aux pa ON pa.numero_partido_fifa = a.numero_fifa
                                AND LOWER(pa.nombre) = LOWER(a.nombre_apostador)
    WHERE f.torneo_id = 2
      AND pa.id IS NULL;
""")
sin_par = cur.fetchone()[0]
lines.append(f"Apuestas sin par en pronosticos_aux: {sin_par}")

# Muestra de diferencias si las hay
if diferencias > 0:
    cur.execute("""
        SELECT a.nombre_apostador, a.numero_fifa,
               a.pred_local, pa.goles_local,
               a.pred_visitante, pa.goles_visitante,
               a.pred_amarillas, pa.amarillas
        FROM apuesta a
        JOIN partido pt ON pt.id = a.partido_id
        JOIN fase f ON f.id = pt.fase_id
        JOIN pronosticos_aux pa ON pa.numero_partido_fifa = a.numero_fifa
                               AND LOWER(pa.nombre) = LOWER(a.nombre_apostador)
        WHERE f.torneo_id = 2
          AND (a.pred_local IS DISTINCT FROM pa.goles_local
            OR a.pred_visitante IS DISTINCT FROM pa.goles_visitante)
        LIMIT 5;
    """)
    lines.append("Muestra diferencias (apostador, num, pred_local, aux_local, pred_vis, aux_vis, pred_amar, aux_amar):")
    for r in cur.fetchall():
        lines.append(f"  {r}")
else:
    lines.append("✅ Contenido identico en ambas tablas")

cur.close()
conn.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
for l in lines:
    print(l)
