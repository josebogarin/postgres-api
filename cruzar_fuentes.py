"""
cruzar_fuentes.py
Cruza partido_stats_fuentes con partido para ver qué fuente acierta más
en cada campo. Muestra tabla de discrepancias con veredicto.
"""
import psycopg2

DB = {"host": "localhost", "port": 5432,
      "dbname": "becbuc", "user": "app_user", "password": "app_password"}

def conectar():
    try:
        return psycopg2.connect(**DB)
    except Exception:
        d = {k: v for k, v in DB.items() if k != "password"}
        return psycopg2.connect(**d)

def main():
    conn = conectar()
    cur = conn.cursor()

    # Traer partidos finalizados con discrepancias entre ESPN y BD
    cur.execute("""
        SELECT
            sf.numero_fifa,
            sf.local, sf.visitante, sf.fecha,
            -- Amarillas
            p.amarillas           AS bd_amar,
            sf.espn_amarillas     AS espn_amar,
            -- Rojas
            p.rojas               AS bd_rojas,
            sf.espn_rojas         AS espn_rojas,
            -- VAR
            p.decisiones_var      AS bd_var,
            sf.espn_var           AS espn_var,
            -- Penales partido
            p.penales_partido     AS bd_pp,
            sf.espn_penales       AS espn_pp,
            -- Minuto primer gol
            p.minuto_primer_gol   AS bd_min,
            sf.espn_minuto        AS espn_min
        FROM partido_stats_fuentes sf
        JOIN partido p ON p.id = sf.partido_id
        WHERE sf.estado = 'finalizado'
          AND sf.espn_amarillas IS NOT NULL
        ORDER BY sf.numero_fifa::integer NULLS LAST
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    partidos = [dict(zip(cols, r)) for r in rows]
    conn.close()

    CAMPOS = [
        ("amar",  "Amarillas (J)", "bd_amar",  "espn_amar"),
        ("rojas", "Rojas (K)",     "bd_rojas", "espn_rojas"),
        ("var",   "VAR (L)",       "bd_var",   "espn_var"),
        ("pp",    "Penales (M)",   "bd_pp",    "espn_pp"),
        ("min",   "Minuto (N)",    "bd_min",   "espn_min"),
    ]

    print(f"\n{'='*90}")
    print(f"DISCREPANCIAS ESPN vs BD — {len(partidos)} partidos con datos ESPN")
    print(f"{'='*90}")

    total_checks = 0
    total_match  = 0
    total_diff   = 0

    discrepancias_detalle = []

    for p in partidos:
        nf    = p["numero_fifa"] or "?"
        label = f"P{nf} {p['local']} vs {p['visitante']}"
        diffs = []

        for clave, nombre, bd_key, espn_key in CAMPOS:
            bd_v   = p.get(bd_key)
            espn_v = p.get(espn_key)

            if bd_v is None or espn_v is None:
                continue

            # Para minuto: comparar con tolerancia ±2 min
            if clave == "min":
                match = abs(bd_v - espn_v) <= 2
            else:
                match = bd_v == espn_v

            total_checks += 1
            if match:
                total_match += 1
            else:
                total_diff += 1
                diffs.append((nombre, bd_v, espn_v))

        if diffs:
            discrepancias_detalle.append((label, diffs))

    # ── Tabla de discrepancias ────────────────────────────────────────────────
    print(f"\n{'Partido':<45} {'Campo':<14} {'BD':>5} {'ESPN':>6} {'Dif':>5}")
    print(f"{'─'*80}")

    for label, diffs in discrepancias_detalle:
        for i, (campo, bd_v, espn_v) in enumerate(diffs):
            partido_str = label if i == 0 else ""
            diff = espn_v - bd_v
            sign = "+" if diff > 0 else ""
            print(f"  {partido_str:<43} {campo:<14} {bd_v:>5} {espn_v:>6} {sign+str(diff):>5}")
        print()

    # ── Resumen por campo ────────────────────────────────────────────────────
    print(f"\n{'='*90}")
    print("RESUMEN POR CAMPO")
    print(f"{'='*90}")
    print(f"\n  {'Campo':<15} {'Checks':>7} {'Match':>7} {'Diff':>7} {'Acuerdo%':>10} {'ESPN>BD':>8} {'ESPN<BD':>8}")
    print(f"  {'─'*65}")

    for clave, nombre, bd_key, espn_key in CAMPOS:
        checks = match_c = diff_c = espn_mas = espn_menos = 0
        for p in partidos:
            bd_v   = p.get(bd_key)
            espn_v = p.get(espn_key)
            if bd_v is None or espn_v is None:
                continue
            checks += 1
            if clave == "min":
                ok = abs(bd_v - espn_v) <= 2
            else:
                ok = bd_v == espn_v
            if ok:
                match_c += 1
            else:
                diff_c += 1
                if espn_v > bd_v:
                    espn_mas += 1
                else:
                    espn_menos += 1

        if checks == 0:
            continue
        pct = 100 * match_c / checks
        print(f"  {nombre:<15} {checks:>7} {match_c:>7} {diff_c:>7} {pct:>9.1f}% {espn_mas:>8} {espn_menos:>8}")

    # ── Patrón ESPN ──────────────────────────────────────────────────────────
    print(f"\n{'='*90}")
    print("PATRÓN: cuando ESPN difiere, ¿sobreestima o subestima?")
    print(f"{'='*90}")
    print("""
  ESPN>BD → ESPN cuenta MÁS que la BD (posible sobreconteo, o BD faltó algo)
  ESPN<BD → ESPN cuenta MENOS que la BD (posible que BD esté inflada, o ESPN perdió algo)
    """)

    print(f"\n  Coincidencia total: {total_match}/{total_checks} "
          f"({100*total_match/total_checks:.1f}%)")
    print(f"  Discrepancias:      {total_diff}/{total_checks} "
          f"({100*total_diff/total_checks:.1f}%)\n")

if __name__ == "__main__":
    main()
