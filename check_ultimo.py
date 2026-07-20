"""
check_ultimo.py
Muestra los últimos partidos finalizados y busca Uruguay vs Cabo Verde.
"""
import sys, io, psycopg2, psycopg2.extras
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

conn = psycopg2.connect(**PG)
cur = conn.cursor()

# Ultimos 10 partidos finalizados por fecha
cur.execute("""
    SELECT
        a.numero_fifa AS num,
        el.nombre AS local,
        p.goles_local AS gl,
        p.goles_visitante AS gv,
        ev.nombre AS visit,
        p.fecha,
        p.estado,
        f.tipo AS fase,
        COUNT(pd.partido_id) AS apostadores_calculados
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN apuesta a ON a.partido_id = p.id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id
    WHERE f.torneo_id = 2
      AND p.estado = 'finalizado'
    GROUP BY a.numero_fifa, el.nombre, p.goles_local, p.goles_visitante,
             ev.nombre, p.fecha, p.estado, f.tipo
    ORDER BY p.fecha DESC
    LIMIT 15
""")
rows = cur.fetchall()

print("=== Ultimos 15 partidos finalizados ===")
print(f"{'#':>4} {'Local':<22} {'Res':^5} {'Visitante':<22} {'Fase':<12} {'Pts?':>6}")
print("─" * 80)
for r in rows:
    num = f"P{r['num']:03d}" if r['num'] else "???"
    res = f"{r['gl']}-{r['gv']}"
    pts = "✓" if (r['apostadores_calculados'] or 0) > 0 else "✗"
    print(f"{num:>4} {(r['local'] or '?')[:20]:<22} {res:^5} {(r['visit'] or '?')[:20]:<22} {r['fase'][:10]:<12} {pts:>6}")

# Buscar específicamente Uruguay y Cabo Verde
print("\n=== Búsqueda: Uruguay / Cabo Verde ===")
cur.execute("""
    SELECT
        a.numero_fifa AS num,
        el.nombre AS local,
        p.goles_local AS gl,
        p.goles_visitante AS gv,
        ev.nombre AS visit,
        p.fecha,
        p.estado,
        COUNT(pd.partido_id) AS con_puntaje
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN apuesta a ON a.partido_id = p.id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id
    WHERE f.torneo_id = 2
      AND (el.nombre ILIKE '%%uruguay%%' OR ev.nombre ILIKE '%%uruguay%%'
           OR el.nombre ILIKE '%%cabo%%' OR ev.nombre ILIKE '%%cabo%%'
           OR el.nombre ILIKE '%%cape%%' OR ev.nombre ILIKE '%%cape%%')
    GROUP BY a.numero_fifa, el.nombre, p.goles_local, p.goles_visitante,
             ev.nombre, p.fecha, p.estado
    ORDER BY p.fecha
""")
rows2 = cur.fetchall()
if rows2:
    for r in rows2:
        num = f"P{r['num']:03d}" if r['num'] else "???"
        res = f"{r['gl']}-{r['gv']}" if r['gl'] is not None else "? - ?"
        pts = "✓ puntaje calculado" if (r['con_puntaje'] or 0) > 0 else "✗ SIN puntaje"
        print(f"  {num} {r['local']} {res} {r['visit']} [{r['estado']}] {pts}")
else:
    print("  No encontrado (revisar nombre del equipo)")
    cur.execute("""
        SELECT nombre FROM equipo
        WHERE nombre ILIKE '%%cape%%' OR nombre ILIKE '%%cabo%%' OR nombre ILIKE '%%verde%%'
    """)
    for r in cur.fetchall():
        print(f"    Equipo en BD: {r['nombre']}")

cur.close()
conn.close()
