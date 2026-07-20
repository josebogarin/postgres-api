"""
Recalcula pj/pg/pe/pp/gf/gc/pts/gd en participacion directamente desde
los partidos finalizados, para todos los grupos del torneo 2.
"""
import subprocess

def psql(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    rows = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    return rows, r.stderr.strip()

def psql_exec(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db, "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip(), r.stderr.strip()

print("=== RECALCULO DIRECTO DE PARTICIPACION ===\n")

# 1. Ver estado actual
rows, _ = psql("""
    SELECT pa.fase_id, f.nombre, COUNT(*) as total,
           SUM(CASE WHEN pa.pj = 3 THEN 1 ELSE 0 END) as con3pj
    FROM participacion pa
    JOIN fase f ON pa.fase_id = f.id
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
    GROUP BY pa.fase_id, f.nombre
    ORDER BY f.nombre
""")

print("Estado ANTES:")
for r in rows:
    cols = r.split("|")
    fid, fname, total, con3pj = cols[0].strip(), cols[1].strip(), cols[2].strip(), cols[3].strip()
    flag = "✅" if total == con3pj else "⚠️"
    print(f"  {flag} {fname:<20} equipos={total}, con_3pj={con3pj}")

print()

# 2. Recalcular via SQL directo
print("Recalculando desde partidos finalizados...")

out, err = psql_exec("""
WITH stats AS (
    -- Partidos donde el equipo es LOCAL
    SELECT pa.id as participacion_id,
           COUNT(CASE WHEN p.estado='finalizado' THEN 1 END) as pj,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_local > p.goles_visitante THEN 1 END) as pg,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_local = p.goles_visitante THEN 1 END) as pe,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_local < p.goles_visitante THEN 1 END) as pp,
           COALESCE(SUM(CASE WHEN p.estado='finalizado' THEN p.goles_local ELSE 0 END), 0) as gf,
           COALESCE(SUM(CASE WHEN p.estado='finalizado' THEN p.goles_visitante ELSE 0 END), 0) as gc
    FROM participacion pa
    JOIN fase f ON pa.fase_id = f.id
    JOIN partido p ON p.fase_id = pa.fase_id
                   AND p.equipo_local_id = pa.equipo_id
                   AND p.torneo_id = 2
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
    GROUP BY pa.id

    UNION ALL

    -- Partidos donde el equipo es VISITANTE
    SELECT pa.id as participacion_id,
           COUNT(CASE WHEN p.estado='finalizado' THEN 1 END) as pj,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_visitante > p.goles_local THEN 1 END) as pg,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_local = p.goles_visitante THEN 1 END) as pe,
           COUNT(CASE WHEN p.estado='finalizado' AND p.goles_visitante < p.goles_local THEN 1 END) as pp,
           COALESCE(SUM(CASE WHEN p.estado='finalizado' THEN p.goles_visitante ELSE 0 END), 0) as gf,
           COALESCE(SUM(CASE WHEN p.estado='finalizado' THEN p.goles_local ELSE 0 END), 0) as gc
    FROM participacion pa
    JOIN fase f ON pa.fase_id = f.id
    JOIN partido p ON p.fase_id = pa.fase_id
                   AND p.equipo_visitante_id = pa.equipo_id
                   AND p.torneo_id = 2
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
    GROUP BY pa.id
),
totales AS (
    SELECT participacion_id,
           SUM(pj) as pj,
           SUM(pg) as pg,
           SUM(pe) as pe,
           SUM(pp) as pp,
           SUM(gf) as gf,
           SUM(gc) as gc,
           SUM(pg)*3 + SUM(pe) as pts
    FROM stats
    GROUP BY participacion_id
)
UPDATE participacion SET
    pj  = t.pj,
    pg  = t.pg,
    pe  = t.pe,
    pp  = t.pp,
    gf  = t.gf,
    gc  = t.gc,
    pts = t.pts
FROM totales t
WHERE participacion.id = t.participacion_id
""")

if 'ERROR' in err:
    print(f"  ERROR: {err}")
else:
    print(f"  OK: {out}")

# 3. Ver estado después
print("\nEstado DESPUES:")
rows, _ = psql("""
    SELECT pa.fase_id, f.nombre, COUNT(*) as total,
           SUM(CASE WHEN pa.pj = 3 THEN 1 ELSE 0 END) as con3pj,
           SUM(pa.pj) as suma_pj
    FROM participacion pa
    JOIN fase f ON pa.fase_id = f.id
    WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%'
    GROUP BY pa.fase_id, f.nombre
    ORDER BY f.nombre
""")

for r in rows:
    cols = r.split("|")
    fid, fname, total, con3pj, spj = cols[0].strip(), cols[1].strip(), cols[2].strip(), cols[3].strip(), cols[4].strip()
    flag = "✅" if total == con3pj else ("⚠️" if int(con3pj) > 0 else "❌")
    print(f"  {flag} {fname:<20} equipos={total}, con_3pj={con3pj}, suma_pj={spj}")

print("\n=== FIN ===")
input("\nPresioná Enter para cerrar...")
