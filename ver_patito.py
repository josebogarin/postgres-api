"""
ver_patito.py
Muestra prediccion vs resultado real vs puntos obtenidos para PATITO,
con enfasis en items que difieren de la planilla (A+4, C+2, D+1, E+1, F+1).
"""
import sys, io, psycopg2, psycopg2.extras
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ALIAS = 'GONZALO'  # PATITO = GONZALO RAÚL JIMÉNEZ NIZ

PG = dict(host="localhost", port=5432, user="app_user",
          password="superpassword", dbname="becbuc",
          cursor_factory=psycopg2.extras.RealDictCursor)

conn = psycopg2.connect(**PG)
cur = conn.cursor()

# Buscar apostador_id por nombre
cur.execute("""
    SELECT DISTINCT a.apostador_id, a.nombre_apostador
    FROM apuesta a
    WHERE UPPER(a.nombre_apostador) ILIKE %s
    LIMIT 5
""", (f'%{ALIAS}%',))
apostadores = cur.fetchall()
if not apostadores:
    print(f"No encontrado: '{ALIAS}'. Nombres disponibles en BD:")
    cur.execute("""
        SELECT DISTINCT nombre_apostador
        FROM apuesta WHERE nombre_apostador IS NOT NULL
        ORDER BY nombre_apostador
    """)
    for r in cur.fetchall():
        print(f"  {r['nombre_apostador']}")
    cur.close(); conn.close(); sys.exit(1)
apost_id = apostadores[0]['apostador_id']
print(f"Apostador: {apostadores[0]['nombre_apostador']} (id={apost_id})\n")

# Totales por item desde puntaje_detalle
cur.execute("""
    SELECT
        SUM(pts_resultado)       AS tot_a,
        SUM(pts_marcador)        AS tot_b,
        SUM(pts_amarillas)       AS tot_c,
        SUM(pts_rojas)           AS tot_d,
        SUM(pts_var)             AS tot_e,
        SUM(pts_penales_partido) AS tot_f,
        SUM(pts_minuto)          AS tot_g,
        SUM(pts_penales_tanda)   AS tot_o,
        COUNT(*)                 AS partidos
    FROM puntaje_detalle
    WHERE apostador_id = %s AND torneo_id = 2
""", (apost_id,))
tots = cur.fetchone()
print(f"TOTALES BD (puntaje_detalle):")
print(f"  A={tots['tot_a']} B={tots['tot_b']} C={tots['tot_c']} "
      f"D={tots['tot_d']} "
      f"E={tots['tot_e']} F={tots['tot_f']} G={tots['tot_g']} "
      f"| partidos={tots['partidos']}")
print(f"  TOTAL PARTIDOS = {sum(v or 0 for k,v in tots.items() if k.startswith('tot_'))}\n")

# Detalle partido por partido
cur.execute("""
    SELECT
        a.numero_fifa           AS num,
        el.nombre               AS local,
        p.goles_local           AS gl,
        p.goles_visitante       AS gv,
        ev.nombre               AS visit,
        p.amarillas             AS r_amar,
        p.rojas                 AS r_rojas,
        p.decisiones_var        AS r_var,
        p.penales_partido       AS r_pen,
        p.minuto_primer_gol     AS r_min,
        a.pred_local            AS p_local,
        a.pred_visitante        AS p_visit,
        a.pred_amarillas        AS p_amar,
        a.pred_rojas            AS p_rojas,
        a.pred_var              AS p_var,
        a.pred_penales_partido  AS p_pen,
        a.pred_minuto_gol       AS p_min,
        pd.pts_resultado        AS pts_a,
        pd.pts_marcador         AS pts_b,
        pd.pts_amarillas        AS pts_c,
        pd.pts_rojas            AS pts_d,
        pd.pts_var              AS pts_e,
        pd.pts_penales_partido  AS pts_f,
        pd.pts_minuto           AS pts_g,
        f.tipo                  AS fase,
        CASE WHEN p.equipo_local_id IN (
            SELECT id FROM equipo WHERE nombre ILIKE '%%paraguay%%'
        ) OR p.equipo_visitante_id IN (
            SELECT id FROM equipo WHERE nombre ILIKE '%%paraguay%%'
        ) THEN 'PY' ELSE '' END AS py
    FROM apuesta a
    JOIN partido p ON p.id = a.partido_id
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id
    WHERE a.apostador_id = %s
      AND f.torneo_id = 2
      AND p.estado = 'finalizado'
    ORDER BY a.numero_fifa
""", (apost_id,))
rows = cur.fetchall()

print(f"{'PID':<5} {'LOCAL':<18} {'REAL':^7} {'PRED':^7} {'VISIT':<18} {'PY':<3} "
      f"{'A':>3} {'B':>3} {'C':>3} {'D':>3} {'E':>3} {'F':>3} {'G':>3} "
      f"{'amar':>5} {'roj':>4} {'var':>4} {'pen':>4} {'min':>4}")
print("─"*120)

for r in rows:
    num  = f"P{str(r['num']).zfill(3)}"
    real = f"{r['gl']}-{r['gv']}"
    pred = f"{r['p_local'] or 0}-{r['p_visit'] or 0}"
    # Marcar amarillas con * si hay diferencia pred vs real
    amar_diff = '*' if (r['p_amar'] or 0) != (r['r_amar'] or 0) else ''
    roj_diff  = '*' if (r['p_rojas'] or 0) != (r['r_rojas'] or 0) else ''
    var_diff  = '*' if (r['p_var'] or 0) != (r['r_var'] or 0) else ''
    pen_diff  = '*' if (r['p_pen'] or 0) != (r['r_pen'] or 0) else ''

    print(f"{num:<5} {(r['local'] or '')[:16]:<18} {real:^7} {pred:^7} "
          f"{(r['visit'] or '')[:16]:<18} {r['py']:<3} "
          f"{r['pts_a'] or 0:>3} {r['pts_b'] or 0:>3} "
          f"{r['pts_c'] or 0:>3} {r['pts_d'] or 0:>3} "
          f"{r['pts_e'] or 0:>3} {r['pts_f'] or 0:>3} "
          f"{r['pts_g'] or 0:>3} "
          f"  {r['r_amar'] or 0:>2}/{r['p_amar'] or 0:<2}{amar_diff:<1}"
          f"  {r['r_rojas'] or 0:>2}/{r['p_rojas'] or 0:<2}{roj_diff:<1}"
          f"  {r['r_var'] or 0:>2}/{r['p_var'] or 0:<2}{var_diff:<1}"
          f"  {r['r_pen'] or 0:>2}/{r['p_pen'] or 0:<2}{pen_diff:<1}"
          f"  {r['r_min'] or '-':>4}/{r['p_min'] or '-'}")

print(f"\n(* = diferencia real vs pred en ese item)")

# Resumen diferencias por item
tot_a = sum(r['pts_a'] or 0 for r in rows)
tot_b = sum(r['pts_b'] or 0 for r in rows)
tot_c = sum(r['pts_c'] or 0 for r in rows)
tot_d = sum(r['pts_d'] or 0 for r in rows)
tot_e = sum(r['pts_e'] or 0 for r in rows)
tot_f = sum(r['pts_f'] or 0 for r in rows)
tot_g = sum(r['pts_g'] or 0 for r in rows)
print(f"\nSUMATORIA: A={tot_a} B={tot_b} C={tot_c} D={tot_d} E={tot_e} F={tot_f} G={tot_g}")
print(f"TOTAL BD: {tot_a+tot_b+tot_c+tot_d+tot_e+tot_f+tot_g}")
print(f"PLANILLA: A=104 B=40 C=7 D=33 E=26 F=32 G=0  TOTAL=242")
print(f"DIFERENCIAS: A={tot_a-104:+} B={tot_b-40:+} C={tot_c-7:+} D={tot_d-33:+} "
      f"E={tot_e-26:+} F={tot_f-32:+} G={tot_g-0:+}")

cur.close()
conn.close()
