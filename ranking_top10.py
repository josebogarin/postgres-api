"""ranking_top10.py - escribe resultado a archivo"""
import psycopg2, psycopg2.extras, traceback, os

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ranking_resultado.txt")
lines = []

try:
    conn = psycopg2.connect(**PG)
    cur = conn.cursor()

    cur.execute("""
        SELECT pd.apostador_id,
            SUM(COALESCE(pts_resultado,0)+COALESCE(pts_marcador,0)+
                COALESCE(pts_amarillas,0)+COALESCE(pts_rojas,0)+
                COALESCE(pts_var,0)+COALESCE(pts_penales_partido,0)+
                COALESCE(pts_minuto,0)+COALESCE(pts_penales_tanda,0)+
                COALESCE(pts_equipo,0)) AS pts_p,
            COUNT(*) FILTER (WHERE pts_marcador > 0) AS plenos,
            COUNT(*) FILTER (WHERE pts_resultado > 0) AS ok
        FROM puntaje_detalle pd
        JOIN partido p ON p.id = pd.partido_id
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = 2
        GROUP BY pd.apostador_id
    """)
    pd_rows = {r['apostador_id']: r for r in cur.fetchall()}

    cur.execute("""
        SELECT DISTINCT ON (apostador_id) apostador_id, nombre_apostador
        FROM apuesta WHERE nombre_apostador IS NOT NULL
        ORDER BY apostador_id, id DESC
    """)
    nombres = {r['apostador_id']: r['nombre_apostador'] for r in cur.fetchall()}

    ranking = sorted(
        [{'aid': aid,
          'n': nombres.get(aid, 'Apostador '+str(aid)),
          'p': int(pd['pts_p'] or 0),
          'pl': int(pd['plenos'] or 0),
          'ok': int(pd['ok'] or 0)}
         for aid, pd in pd_rows.items()],
        key=lambda x: x['p'], reverse=True
    )

    lines.append("=== RANKING BECBUC Copa del Mundo 2026 ===")
    lines.append(f"{'#':>3}  {'Nombre':<35} {'Pts':>6}  {'Plenos':>6}  {'OK':>4}")
    lines.append("-" * 62)
    for i, r in enumerate(ranking[:15], 1):
        nombre = r['n'][:33] if r['n'] else str(r['aid'])
        lines.append(f"{i:>3}. {nombre:<35} {r['p']:>6}  {r['pl']:>6}  {r['ok']:>4}")
    lines.append(f"\nTotal: {len(ranking)} apostadores")

    # Ultimo partido calculado
    cur.execute("""
        SELECT el.nombre AS local, p.goles_local, p.goles_visitante, ev.nombre AS visit, p.fecha
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id=2 AND p.estado='finalizado'
        ORDER BY p.fecha DESC LIMIT 1
    """)
    ult = cur.fetchone()
    if ult:
        lines.append(f"Ultimo partido: {ult['local']} {ult['goles_local']}-{ult['goles_visitante']} {ult['visit']} ({ult['fecha'].strftime('%d/%m/%Y') if ult['fecha'] else '?'})")

    cur.close()
    conn.close()

except Exception:
    lines.append("ERROR:")
    lines.append(traceback.format_exc())

# Escribir al archivo
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print("Listo. Ver ranking_top10_log.txt")
