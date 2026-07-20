import subprocess, json

def psql(sql):
    cmd = ["docker", "exec", "-i", "core-postgres",
           "psql", "-U", "app_user", "-d", "becbuc",
           "--tuples-only", "--no-align", "-F", "|"]
    r = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=30)
    return [row.split("|") for row in r.stdout.strip().splitlines() if row.strip()]

rows = psql("""
    SELECT
      COUNT(*) AS total_apuestas,
      COUNT(a.pred_penales_partido) AS con_pred_pen,
      MIN(a.pred_penales_partido) AS min_val,
      MAX(a.pred_penales_partido) AS max_val,
      COUNT(pd.pts_penales_partido) FILTER (WHERE pd.pts_penales_partido IS NOT NULL AND pd.pts_penales_partido > 0) AS con_pts_m
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
    WHERE p.torneo_id = 2
      AND p.estado = 'finalizado'
""")

if rows:
    r = rows[0]
    total       = r[0].strip()
    con_pred    = r[1].strip()
    min_val     = r[2].strip()
    max_val     = r[3].strip()
    con_pts_m   = r[4].strip()
    print(f"\n=== CHECK PENALES POR JUEGO (M) ===")
    print(f"  Apuestas en partidos finalizados : {total}")
    print(f"  Con pred_penales_partido         : {con_pred}  (rango: {min_val} - {max_val})")
    print(f"  Con pts_penales_partido > 0      : {con_pts_m}")
    faltantes = int(total) - int(con_pred) if total.isdigit() and con_pred.isdigit() else "?"
    if faltantes == 0:
        print(f"\n  ✅ DATOS COMPLETOS — solo regenerar el Excel")
    elif int(con_pred) == 0:
        print(f"\n  ❌ SIN DATOS — reimportar desde Excel de apostadores")
    else:
        print(f"\n  ⚠️  DATOS PARCIALES ({faltantes} apuestas sin pred_penales_partido)")
else:
    print("Sin datos o torneo_id incorrecto")
