"""Pronosticos + resultado + puntos de Quiroga para partidos finalizados."""
import psycopg2

DB = dict(host="localhost", port=5432, dbname="becbuc", user="app_user", password="superpassword")
OUT = r"C:\proyecto FAST API\resultado_quiroga.txt"
lines = []

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Verificar nombre exacto
cur.execute("SELECT DISTINCT nombre_apostador, apostador_id FROM apuesta WHERE LOWER(nombre_apostador) LIKE '%quiroga%';")
apostadores = cur.fetchall()
lines.append(f"Apostador(es) encontrados: {apostadores}")
if not apostadores:
    lines.append("No se encontro apostador con 'quiroga'")
    with open(OUT, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    print("\n".join(lines)); exit()

nombre_ap, apostador_id = apostadores[0]
lines.append(f"Usando: {nombre_ap} (id={apostador_id})\n")

# Pronosticos + resultado + puntaje_detalle
cur.execute("""
    SELECT
        a.numero_fifa                       AS num,
        el.nombre                           AS local,
        COALESCE(pt.goles_local, 0)         AS rl,
        COALESCE(pt.goles_visitante, 0)     AS rv,
        ev.nombre                           AS visitante,
        COALESCE(a.pred_local, 0)           AS pl,
        COALESCE(a.pred_visitante, 0)       AS pv,
        COALESCE(a.pred_amarillas, 0)       AS p_amar,
        COALESCE(pt.amarillas, 0)           AS r_amar,
        COALESCE(a.pred_rojas, 0)           AS p_roj,
        COALESCE(pt.rojas, 0)               AS r_roj,
        COALESCE(a.pred_var, 0)             AS p_var,
        COALESCE(pt.decisiones_var, 0)      AS r_var,
        COALESCE(a.pred_minuto_gol, 0)      AS p_min,
        COALESCE(pt.minuto_primer_gol, 0)   AS r_min,
        -- puntaje_detalle
        COALESCE(pd.pts_resultado, 0)       AS pts_H,
        COALESCE(pd.pts_marcador, 0)        AS pts_I,
        COALESCE(pd.pts_amarillas, 0)       AS pts_J,
        COALESCE(pd.pts_rojas, 0)           AS pts_K,
        COALESCE(pd.pts_var, 0)             AS pts_L,
        COALESCE(pd.pts_penales_partido, 0) AS pts_M,
        COALESCE(pd.pts_minuto, 0)          AS pts_N,
        COALESCE(pd.pts_penales_tanda, 0)   AS pts_O
    FROM apuesta a
    JOIN partido pt  ON pt.id  = a.partido_id
    JOIN fase f      ON f.id   = pt.fase_id
    JOIN equipo el   ON el.id  = pt.equipo_local_id
    JOIN equipo ev   ON ev.id  = pt.equipo_visitante_id
    LEFT JOIN puntaje_detalle pd
           ON pd.partido_id   = pt.id
          AND pd.apostador_id = a.apostador_id
    WHERE f.torneo_id = 2
      AND a.apostador_id = %s
      AND pt.estado = 'finalizado'
    ORDER BY a.numero_fifa;
""", (apostador_id,))

rows = cur.fetchall()
lines.append(f"Partidos finalizados: {len(rows)}\n")

hdr = f"{'#':>3}  {'Local':22s} {'Res':>7}  {'Pred':>7}  {'Visitante':22s}  {'J':>4} {'K':>4} {'VAR':>4} {'Min':>5}   H   I   J   K   L   M   N   O  Total"
lines.append(hdr)
lines.append("-" * len(hdr))

total_pts = 0
for r in rows:
    num, local, rl, rv, visitante, pl, pv, p_amar, r_amar, p_roj, r_roj, p_var, r_var, p_min, r_min, pts_H, pts_I, pts_J, pts_K, pts_L, pts_M, pts_N, pts_O = r
    total = pts_H + pts_I + pts_J + pts_K + pts_L + pts_M + pts_N + pts_O
    total_pts += total
    res_str  = f"{rl}-{rv}"
    pred_str = f"{pl}-{pv}"
    amar_str = f"{p_amar}/{r_amar}"
    roj_str  = f"{p_roj}/{r_roj}"
    var_str  = f"{p_var}/{r_var}"
    min_str  = f"{p_min}/{r_min}"
    lines.append(
        f"{num:>3}  {local:22s} {res_str:>7}  {pred_str:>7}  {visitante:22s}"
        f"  {amar_str:>4} {roj_str:>4} {var_str:>4} {min_str:>5}"
        f"  {pts_H:>3} {pts_I:>3} {pts_J:>3} {pts_K:>3} {pts_L:>3} {pts_M:>3} {pts_N:>3} {pts_O:>3}  {total:>4}"
    )

lines.append("-" * len(hdr))
lines.append(f"TOTAL PUNTOS: {total_pts}")

cur.close()
conn.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
for l in lines:
    print(l)
