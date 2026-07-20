"""
check_estado.py
Verifica el estado actual de puntajes en BD.
"""
import sys, io, psycopg2, psycopg2.extras
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

conn = psycopg2.connect(**PG)
cur = conn.cursor()

# Estado partidos
cur.execute("""
    SELECT
        COUNT(*) FILTER (WHERE p.estado='finalizado') AS finalizados,
        COUNT(*) FILTER (WHERE p.estado='en_juego') AS en_juego,
        COUNT(*) FILTER (WHERE p.estado='programado') AS programados,
        COUNT(*) AS total,
        MAX(p.fecha) AS ultimo_partido
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    WHERE f.torneo_id = 2
""")
r = cur.fetchone()
print("=== Estado partidos (torneo 2) ===")
print(f"  Finalizados:  {r['finalizados']}")
print(f"  En juego:     {r['en_juego']}")
print(f"  Programados:  {r['programados']}")
print(f"  Total:        {r['total']}")
print(f"  Ultimo:       {r['ultimo_partido']}")

# puntaje_detalle
cur.execute("""
    SELECT COUNT(DISTINCT partido_id) AS partidos_calculados,
           COUNT(DISTINCT apostador_id) AS apostadores
    FROM puntaje_detalle WHERE torneo_id = 2
""")
r2 = cur.fetchone()
print(f"\n=== puntaje_detalle ===")
print(f"  Partidos calculados: {r2['partidos_calculados']}")
print(f"  Apostadores:         {r2['apostadores']}")

# Top 10
cur.execute("""
    SELECT a.nombre_apostador,
           SUM(pd.pts_resultado + pd.pts_marcador + pd.pts_amarillas + pd.pts_rojas + pd.pts_var +
               COALESCE(pd.pts_penales_partido,0) + pd.pts_minuto + pd.pts_penales_tanda) AS tot
    FROM puntaje_detalle pd
    JOIN (SELECT DISTINCT apostador_id, nombre_apostador FROM apuesta WHERE nombre_apostador IS NOT NULL) a
      ON a.apostador_id = pd.apostador_id
    WHERE pd.torneo_id = 2
    GROUP BY a.nombre_apostador
    ORDER BY tot DESC
    LIMIT 10
""")
print(f"\n=== Top 10 ranking actual (BD) ===")
for i, r in enumerate(cur.fetchall(), 1):
    print(f"  {i:2}. {r['nombre_apostador']}: {r['tot']} pts")

# Ultimo sync
try:
    cur.execute("""
        SELECT created_at, contexto, ok
        FROM api_sync_log
        ORDER BY created_at DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    print(f"\n=== Ultimos sync API-Football ===")
    for r in rows:
        print(f"  {r['created_at']} | ok={r['ok']} | {r['contexto']}")
except Exception as e:
    print(f"\napi_sync_log no disponible: {e}")

# Partidos finalizados hoy
cur.execute("""
    SELECT p.id, el.nombre AS local, p.goles_local, p.goles_visitante, ev.nombre AS visit,
           p.fecha, p.estado
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE f.torneo_id = 2
      AND p.estado IN ('finalizado', 'en_juego')
    ORDER BY p.fecha DESC
    LIMIT 10
""")
rows = cur.fetchall()
print(f"\n=== Ultimos 10 partidos (finalizado/en_juego) ===")
for r in rows:
    print(f"  {r['fecha']} | {r['local']} {r['goles_local']}-{r['goles_visitante']} {r['visit']} [{r['estado']}]")

cur.close()
conn.close()
print("\n=== FIN ===")
