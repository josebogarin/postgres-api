"""
Diagnóstico de puntaje_detalle — escribe solo a log file.
"""
import subprocess

OUT = []

def q(sql, db="becbuc"):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", db,
           "-c", sql, "--tuples-only", "--no-align", "--field-separator=|"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return [l.strip() for l in r.stdout.strip().splitlines() if l.strip()], r.stderr.strip()

def log(msg=""):
    OUT.append(msg)
    print(msg)

log("=" * 60)
log("DIAGNÓSTICO DE PUNTAJES (torneo_id=2)")
log("=" * 60)

# 1. puntaje_detalle resumen
rows, _ = q("""
    SELECT COUNT(*) , COUNT(DISTINCT apostador_id),
           COUNT(DISTINCT partido_id), COALESCE(SUM(pts_total),0),
           SUM(CASE WHEN pts_total>0 THEN 1 ELSE 0 END),
           SUM(CASE WHEN pts_total=0 THEN 1 ELSE 0 END)
    FROM puntaje_detalle WHERE torneo_id=2
""")
if rows:
    c = rows[0].split("|")
    log(f"\n1. puntaje_detalle:")
    log(f"   Filas={c[0]}  Apostadores={c[1]}  Partidos={c[2]}")
    log(f"   pts_total_acum={c[3]}  con_puntos={c[4]}  sin_puntos={c[5]}")
else:
    log("\n1. puntaje_detalle: SIN DATOS o tabla no existe!")

# 2. Partidos finalizados
rows, _ = q("""
    SELECT COUNT(*),
           SUM(CASE WHEN goles_local IS NOT NULL THEN 1 ELSE 0 END)
    FROM partido WHERE torneo_id=2 AND estado='finalizado'
""")
if rows:
    c = rows[0].split("|")
    log(f"\n2. Partidos finalizados: total={c[0]}, con_goles={c[1]}")

# 3. Apuestas para partidos finalizados
rows, _ = q("""
    SELECT COUNT(*), COUNT(DISTINCT a.apostador_id)
    FROM apuesta a
    JOIN partido p ON p.id=a.partido_id
    WHERE p.torneo_id=2 AND p.estado='finalizado' AND p.goles_local IS NOT NULL
""")
if rows:
    c = rows[0].split("|")
    log(f"\n3. Apuestas partidos finalizados: total={c[0]}, apostadores={c[1]}")

# 4. Top 10 apostadores por pts_total
rows, _ = q("""
    SELECT apostador_id,
           SUM(pts_resultado) as h,
           SUM(pts_marcador) as i,
           SUM(COALESCE(pts_amarillas,0)) as j,
           SUM(COALESCE(pts_rojas,0)) as k,
           SUM(COALESCE(pts_var,0)) as l,
           SUM(COALESCE(pts_penales_partido,0)) as m,
           SUM(COALESCE(pts_minuto,0)) as n,
           SUM(COALESCE(pts_penales_tanda,0)) as o,
           SUM(pts_total) as total
    FROM puntaje_detalle
    WHERE torneo_id=2
    GROUP BY apostador_id
    ORDER BY total DESC LIMIT 10
""")
log(f"\n4. Top 10 apostadores (desde puntaje_detalle):")
if rows:
    log(f"   {'ApostID':>8} {'H':>5} {'I':>5} {'J':>4} {'K':>4} {'L':>4} {'M':>4} {'N':>4} {'O':>4} {'TOTAL':>6}")
    for r in rows:
        c = r.split("|")
        log(f"   {c[0]:>8} {c[1]:>5} {c[2]:>5} {c[3]:>4} {c[4]:>4} {c[5]:>4} {c[6]:>4} {c[7]:>4} {c[8]:>4} {c[9]:>6}")
else:
    log("   SIN DATOS!")

# 5. Distribución de pts_total
rows, _ = q("""
    SELECT pts_total, COUNT(*) as cnt
    FROM puntaje_detalle WHERE torneo_id=2
    GROUP BY pts_total ORDER BY pts_total DESC LIMIT 12
""")
log(f"\n5. Distribución pts_total:")
for r in rows:
    c = r.split("|")
    log(f"   pts={c[0]:>3}: {c[1]:>5} filas")

# 6. Verificar campos del scoring engine — primer partido finalizado
rows, _ = q("""
    SELECT p.numero_fifa, p.goles_local, p.goles_visitante,
           p.amarillas, p.rojas, p.decisiones_var, p.penales_partido,
           p.minuto_primer_gol, f.tipo
    FROM partido p JOIN fase f ON f.id=p.fase_id
    WHERE p.torneo_id=2 AND p.estado='finalizado' AND p.goles_local IS NOT NULL
    ORDER BY p.numero_fifa LIMIT 5
""")
log(f"\n6. Primeros 5 partidos finalizados (datos BD):")
for r in rows:
    c = r.split("|")
    log(f"   P{c[0]:>3} {c[1]}-{c[2]} | amar={c[3]} rojas={c[4]} var={c[5]} pp={c[6]} min={c[7]} fase={c[8]}")

# 7. Un apostador — sus puntajes detalle (apostador_id=9, primer apostador)
rows, _ = q("""
    SELECT p.numero_fifa,
           pd.pts_resultado, pd.pts_marcador, pd.pts_total,
           a.pred_local, a.pred_visitante, p.goles_local, p.goles_visitante
    FROM puntaje_detalle pd
    JOIN partido p ON p.id=pd.partido_id
    JOIN apuesta a ON a.partido_id=p.id AND a.apostador_id=pd.apostador_id
    WHERE pd.torneo_id=2 AND pd.apostador_id=9
    ORDER BY p.numero_fifa LIMIT 15
""")
log(f"\n7. Apostador id=9 — primeros 15 partidos:")
if rows:
    log(f"   {'P#':>3} {'H':>3} {'I':>3} {'Tot':>3}  pred vs real")
    for r in rows:
        c = r.split("|")
        log(f"   P{c[0]:>2} {c[1]:>3} {c[2]:>3} {c[3]:>3}  {c[4]}-{c[5]} vs {c[6]}-{c[7]}")
else:
    log("   Sin datos para apostador_id=9")

log(f"\n{'='*60}")
log("FIN DIAGNÓSTICO")
log(f"{'='*60}")

# Escribir al archivo
with open("diag_puntajes_log.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(OUT))

print("LOG ESCRITO: diag_puntajes_log.txt")
