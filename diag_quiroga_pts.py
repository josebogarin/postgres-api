"""Compara las 3 fuentes de puntaje para Quiroga."""
import psycopg2

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("SELECT apostador_id FROM apuesta WHERE LOWER(nombre_apostador) LIKE '%quiroga%' LIMIT 1;")
apostador_id = cur.fetchone()[0]
print(f"apostador_id = {apostador_id}")

# FUENTE 1: apuesta.puntos (cache por fila)
cur.execute("""
    SELECT SUM(a.puntos) FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    WHERE f.torneo_id = 2 AND a.apostador_id = %s AND pt.estado = 'finalizado';
""", (apostador_id,))
print(f"FUENTE 1 - SUM(apuesta.puntos):       {cur.fetchone()[0]}")

# FUENTE 2: puntaje_detalle (scoring engine calculado)
cur.execute("""
    SELECT SUM(
        COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
        COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
        COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
        COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0)
    )
    FROM puntaje_detalle pd
    JOIN partido pt ON pt.id = pd.partido_id
    JOIN fase f ON f.id = pt.fase_id
    WHERE f.torneo_id = 2 AND pd.apostador_id = %s AND pt.estado = 'finalizado';
""", (apostador_id,))
print(f"FUENTE 2 - SUM(puntaje_detalle.*):    {cur.fetchone()[0]}")

# FUENTE 3: ranking endpoint (puntos_total desde puntaje_detalle via ranking query)
cur.execute("""
    SELECT puntos_total FROM (
        SELECT pd.apostador_id,
               SUM(COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
                   COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
                   COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
                   COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0)) AS puntos_total
        FROM puntaje_detalle pd
        JOIN partido pt ON pt.id = pd.partido_id
        JOIN fase f ON f.id = pt.fase_id
        WHERE f.torneo_id = 2
        GROUP BY pd.apostador_id
    ) t WHERE apostador_id = %s;
""", (apostador_id,))
print(f"FUENTE 3 - ranking todos partidos:    {cur.fetchone()[0]}")

# Desglose por partido: apuesta.puntos vs sum(puntaje_detalle)
print("\nPartido  apuesta.puntos  pd_sum  diff")
cur.execute("""
    SELECT a.numero_fifa,
           COALESCE(a.puntos, 0) AS ap_pts,
           COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
           COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
           COALESCE(pd.pts_var,0) + COALESCE(pd.pts_penales_partido,0) +
           COALESCE(pd.pts_minuto,0) + COALESCE(pd.pts_penales_tanda,0) AS pd_pts
    FROM apuesta a
    JOIN partido pt ON pt.id = a.partido_id
    JOIN fase f ON f.id = pt.fase_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = pt.id AND pd.apostador_id = a.apostador_id
    WHERE f.torneo_id = 2 AND a.apostador_id = %s AND pt.estado = 'finalizado'
    ORDER BY a.numero_fifa;
""", (apostador_id,))
for num, ap, pd in cur.fetchall():
    diff = ap - pd
    flag = " <<<" if diff != 0 else ""
    print(f"  #{num:>3}  apuesta={ap:>3}  pd={pd:>3}  diff={diff:>3}{flag}")

cur.close()
conn.close()
