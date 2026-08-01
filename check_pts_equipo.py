import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2, psycopg2.extras

OUT = _osp.path.join(_BASE, 'check_pts_equipo.txt')

try:
    conn = psycopg2.connect("host=localhost port=5432 dbname=becbuc user=app_user password=superpassword")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    lines = []

    # pts_equipo en R32
    cur.execute("""
        SELECT
            COALESCE(SUM(pd.pts_equipo), 0) AS pts_total,
            COUNT(CASE WHEN pd.pts_equipo > 0 THEN 1 END) AS filas_con_pts,
            COUNT(*) AS total_filas
        FROM puntaje_detalle pd
        JOIN partido p ON p.id = pd.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2 AND f.tipo ILIKE 'ronda32'
    """)
    r = cur.fetchone()
    lines.append(f"R32 pts_equipo: total={r['pts_total']} | filas_con_pts={r['filas_con_pts']} | total_filas={r['total_filas']}")

    # Ver si apostador_clasificados tiene datos de grupos (P)
    try:
        cur.execute("""
            SELECT COUNT(*) AS n, SUM(aciertos) AS aciertos_total
            FROM apostador_clasificados
            WHERE torneo_id = 2 AND fase_tipo = 'grupo'
        """)
        r2 = cur.fetchone()
        lines.append(f"apostador_clasificados (grupos): n={r2['n']} | aciertos_total={r2['aciertos_total']}")
    except Exception as e2:
        lines.append(f"apostador_clasificados (grupos): ERROR={e2}")

    # Ver si hay datos de ronda32
    try:
        cur.execute("""
            SELECT COUNT(*) AS n FROM apostador_clasificados
            WHERE torneo_id = 2 AND fase_tipo = 'ronda32'
        """)
        r3 = cur.fetchone()
        lines.append(f"apostador_clasificados ronda32: n={r3['n']}")
    except Exception as e3:
        lines.append(f"apostador_clasificados ronda32: ERROR={e3}")

    # Top apostadores por pts_equipo R32
    cur.execute("""
        SELECT pd.apostador_id, SUM(pd.pts_equipo) AS pts_eq
        FROM puntaje_detalle pd
        JOIN partido p ON p.id = pd.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2 AND f.tipo ILIKE 'ronda32'
        GROUP BY pd.apostador_id
        ORDER BY pts_eq DESC
        LIMIT 5
    """)
    top = cur.fetchall()
    lines.append("Top 5 apostadores pts_equipo R32:")
    for row in top:
        lines.append(f"  id={row['apostador_id']}: {row['pts_eq']} pts")

    conn.close()
    result = "\n".join(lines)
    print(result)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(result)

except Exception as e:
    msg = f"ERROR: {e}"
    print(msg)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(msg)
