"""
diag_quiroga.py
Compara puntaje sistema vs Excel para Quiroga.
Ejecutar: python diag_quiroga.py
"""
import subprocess, sys

def psql(sql):
    r = subprocess.run(
        ["docker","exec","-i","core-postgres","psql","-U","app_user","-d","becbuc",
         "-t","-A","-F","\t","-c", sql],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print("ERROR psql:", r.stderr); sys.exit(1)
    return [l.split("\t") for l in r.stdout.strip().splitlines() if l]

# 1. Encontrar Quiroga
rows = psql("""
    SELECT id, alias, nombre
    FROM apostador
    WHERE LOWER(alias) LIKE '%quiroga%' OR LOWER(nombre) LIKE '%quiroga%'
""")
if not rows:
    print("No se encontró apostador 'quiroga'. Revisá el nombre exacto:")
    all_ap = psql("SELECT id, alias, nombre FROM apostador ORDER BY id")
    for r in all_ap:
        print(f"  id={r[0]}  alias={r[1]}  nombre={r[2]}")
    sys.exit(1)

apo_id, alias, nombre = rows[0]
print(f"=== Quiroga: id={apo_id} alias={alias} nombre={nombre} ===\n")

# 2. Totales por concepto en puntaje_detalle
tot = psql(f"""
    SELECT
        SUM(pts_resultado)                    AS H,
        SUM(pts_marcador)                     AS I,
        SUM(COALESCE(pts_amarillas,0))        AS J,
        SUM(COALESCE(pts_rojas,0))            AS K,
        SUM(COALESCE(pts_var,0))              AS L,
        SUM(COALESCE(pts_penales_partido,0))  AS M,
        SUM(COALESCE(pts_minuto,0))           AS N,
        SUM(COALESCE(pts_penales_tanda,0))    AS O,
        SUM(pts_resultado + pts_marcador
            + COALESCE(pts_amarillas,0)
            + COALESCE(pts_rojas,0)
            + COALESCE(pts_var,0)
            + COALESCE(pts_penales_partido,0)
            + COALESCE(pts_minuto,0)
            + COALESCE(pts_penales_tanda,0))  AS total_partidos
    FROM puntaje_detalle
    WHERE apostador_id = {apo_id}
""")
if tot and tot[0][0] is not None:
    r = tot[0]
    print(f"--- Puntajes sistema (puntaje_detalle) ---")
    print(f"  H(resultado)  = {r[0]}")
    print(f"  I(exacto)     = {r[1]}")
    print(f"  J(amarillas)  = {r[2]}")
    print(f"  K(rojas)      = {r[3]}")
    print(f"  L(VAR)        = {r[4]}")
    print(f"  M(pen.partido)= {r[5]}")
    print(f"  N(minuto gol) = {r[6]}")
    print(f"  O(pen.tanda)  = {r[7]}")
    print(f"  TOTAL partidos= {r[8]}")
else:
    print("  (sin datos en puntaje_detalle)")

# 3. Globales
glob = psql(f"""
    SELECT pts_campeon, pts_finalistas, pts_goleador, pts_peor_equipo,
           pts_mayor_goleada, pts_etapa_paraguay, pts_goles_paraguay, pts_total
    FROM puntaje_global
    WHERE apostador_id = {apo_id}
    LIMIT 1
""")
print(f"\n--- Globales (puntaje_global) ---")
if glob:
    g = glob[0]
    print(f"  A(campeon)    = {g[0]}")
    print(f"  B(finalistas) = {g[1]}")
    print(f"  C(goleador)   = {g[2]}")
    print(f"  D(peor equipo)= {g[3]}")
    print(f"  E(goleada)    = {g[4]}")
    print(f"  F(etapa PY)   = {g[5]}")
    print(f"  G(goles PY)   = {g[6]}")
    print(f"  TOTAL globales= {g[7]}")
else:
    print("  (sin datos en puntaje_global)")

# 4. Detalle partido a partido (solo partidos con puntos)
print(f"\n--- Detalle por partido (solo con pts > 0) ---")
print(f"  {'P#':<4} {'Local':<18} {'Real':<7} {'Pred':<7} {'Visitante':<18}  H  I  J  K  L  M  N  O  Tot")
print("  " + "-"*95)

detalle = psql(f"""
    SELECT
        p.numero,
        COALESCE(el.nombre_es, el.nombre) AS local,
        p.goles_local,
        p.goles_visitante,
        COALESCE(ev.nombre_es, ev.nombre) AS visitante,
        a.pred_local, a.pred_visitante,
        pd.pts_resultado,
        pd.pts_marcador,
        COALESCE(pd.pts_amarillas,0),
        COALESCE(pd.pts_rojas,0),
        COALESCE(pd.pts_var,0),
        COALESCE(pd.pts_penales_partido,0),
        COALESCE(pd.pts_minuto,0),
        COALESCE(pd.pts_penales_tanda,0),
        pd.pts_resultado + pd.pts_marcador
          + COALESCE(pd.pts_amarillas,0)
          + COALESCE(pd.pts_rojas,0)
          + COALESCE(pd.pts_var,0)
          + COALESCE(pd.pts_penales_partido,0)
          + COALESCE(pd.pts_minuto,0)
          + COALESCE(pd.pts_penales_tanda,0) AS pts_total
    FROM puntaje_detalle pd
    JOIN partido p ON p.id = pd.partido_id
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    JOIN apuesta a ON a.partido_id = pd.partido_id AND a.apostador_id = pd.apostador_id
    WHERE pd.apostador_id = {apo_id}
    ORDER BY p.numero
""")

total_check = 0
for r in detalle:
    pts = [int(x) if x is not None else 0 for x in r[7:15]]
    tot_p = int(r[15]) if r[15] is not None else 0
    total_check += tot_p
    real = f"{r[2]}-{r[3]}"
    pred = f"{r[5]}-{r[6]}"
    if tot_p > 0:
        print(f"  P{r[0]:<3} {str(r[1])[:16]:<18} {real:<7} {pred:<7} {str(r[4])[:16]:<18} "
              f"{pts[0]:>2} {pts[1]:>2} {pts[2]:>2} {pts[3]:>2} {pts[4]:>2} {pts[5]:>2} {pts[6]:>2} {pts[7]:>2} {tot_p:>4}")

print(f"\n  Suma verificada desde detalle: {total_check}")

# 5. Apuestas con pred_amarillas / pred_var para identificar fuente de J y L
print(f"\n--- Bonus items (pred vs real) para partidos con pts en J/K/L/M ---")
bonus = psql(f"""
    SELECT
        p.numero,
        COALESCE(el.nombre_es, el.nombre),
        a.pred_amarillas, p.amarillas,
        a.pred_rojas,     p.rojas,
        a.pred_var,       p.decisiones_var,
        a.pred_penales_partido, p.penales_partido,
        COALESCE(pd.pts_amarillas,0),
        COALESCE(pd.pts_rojas,0),
        COALESCE(pd.pts_var,0),
        COALESCE(pd.pts_penales_partido,0)
    FROM puntaje_detalle pd
    JOIN partido p ON p.id = pd.partido_id
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN apuesta a ON a.partido_id = pd.partido_id AND a.apostador_id = pd.apostador_id
    WHERE pd.apostador_id = {apo_id}
      AND (COALESCE(pd.pts_amarillas,0) > 0 OR COALESCE(pd.pts_rojas,0) > 0
           OR COALESCE(pd.pts_var,0) > 0 OR COALESCE(pd.pts_penales_partido,0) > 0)
    ORDER BY p.numero
""")
print(f"  {'P#':<4} {'Local':<18}  predJ realJ  predK realK  predL realL  predM realM  ptsJ ptsK ptsL ptsM")
for r in bonus:
    print(f"  P{r[0]:<3} {str(r[1])[:16]:<18}  "
          f"{str(r[2]):<5} {str(r[3]):<6}  "
          f"{str(r[4]):<5} {str(r[5]):<6}  "
          f"{str(r[6]):<5} {str(r[7]):<6}  "
          f"{str(r[8]):<5} {str(r[9]):<6}  "
          f"{r[10]:>4} {r[11]:>4} {r[12]:>4} {r[13]:>4}")
