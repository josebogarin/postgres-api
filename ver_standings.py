"""
Muestra standings actuales de grupos y detecta equipos con pj < 3 en grupos completos.
"""
import subprocess

def psql(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

print("=== STANDINGS GRUPOS - EQUIPOS PJ < 3 EN GRUPOS COMPLETOS ===\n")

# Grupos donde todos los partidos estan finalizados (6 partidos finalizados = grupo completo)
rows, _ = psql("""
    SELECT f.id, f.nombre, COUNT(p.id) as total_fin
    FROM fase f
    JOIN partido p ON p.fase_id = f.id AND p.torneo_id = 2
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
      AND p.estado = 'finalizado'
    GROUP BY f.id, f.nombre
    HAVING COUNT(p.id) = 6
    ORDER BY f.nombre
""")

if not rows:
    print("No hay grupos con 6 partidos finalizados aun.")
else:
    grupos_completos = {}
    for r in rows:
        cols = r.split("|")
        grupos_completos[cols[0].strip()] = cols[1].strip()

    print(f"Grupos completos (6 partidos finalizados): {len(grupos_completos)}")
    for fid, nombre in grupos_completos.items():
        print(f"  {nombre}")

    print("\n--- Equipos con pj < 3 en esos grupos ---")
    ids_sql = ",".join(grupos_completos.keys())
    rows2, _ = psql(f"""
        SELECT f.nombre, e.nombre, pa.pj, pa.pts, pa.gf, pa.gc,
               (pa.gf - pa.gc) as gd
        FROM participacion pa
        JOIN fase f ON pa.fase_id = f.id
        JOIN equipo e ON pa.equipo_id = e.id
        WHERE pa.fase_id IN ({ids_sql})
          AND pa.pj < 3
        ORDER BY f.nombre, pa.pts DESC
    """)

    if not rows2:
        print("  Ningun equipo con pj < 3 en grupos completos. ✅")
    else:
        for r in rows2:
            cols = r.split("|")
            print(f"  {cols[0]} | {cols[1]:<30} pj={cols[2]} pts={cols[3]} gf={cols[4]} gc={cols[5]} gd={cols[6]}")

print("\n=== TODOS LOS GRUPOS - RESUMEN ===")
rows3, _ = psql("""
    SELECT f.nombre,
           SUM(CASE WHEN pa.pj = 3 THEN 1 ELSE 0 END) as equipos_3pj,
           COUNT(pa.id) as total_equipos,
           (SELECT COUNT(*) FROM partido p2 WHERE p2.fase_id = f.id AND p2.estado='finalizado') as pts_fin
    FROM fase f
    JOIN participacion pa ON pa.fase_id = f.id
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
    GROUP BY f.id, f.nombre
    ORDER BY f.nombre
""")
for r in rows3:
    cols = r.split("|")
    ok = "✅" if cols[1].strip() == cols[2].strip() else "⚠️"
    print(f"  {ok} {cols[0]:<20} equipos_con_3pj={cols[1].strip()}/{cols[2].strip()} partidos_fin={cols[3].strip()}")

print("\n=== FIN ===")
input("\nPresioná Enter para cerrar...")
