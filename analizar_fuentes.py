"""
analizar_fuentes.py
Compara las 3 fuentes (API-Football, ESPN, SofaScore) contra los valores
finales en partido_stats_fuentes y determina cuál es más confiable por campo.
"""
import psycopg2
from collections import defaultdict

DB = {
    "host": "localhost", "port": 5432,
    "dbname": "becbuc", "user": "app_user", "password": "app_password"
}

CAMPOS = ["amarillas", "rojas", "var", "penales"]
FUENTES = ["api", "espn", "ss"]
FUENTE_LABEL = {"api": "API-Football", "espn": "ESPN", "ss": "SofaScore"}

def conectar():
    try:
        return psycopg2.connect(**DB)
    except Exception as e:
        # Intentar sin password (trust auth)
        d = {k: v for k, v in DB.items() if k != "password"}
        return psycopg2.connect(**d)

def main():
    conn = conectar()
    cur = conn.cursor()

    # Traer todos los partidos finalizados
    cur.execute("""
        SELECT
            sf.numero_fifa, sf.local, sf.visitante, sf.fecha,
            sf.api_amarillas,  sf.espn_amarillas,  sf.ss_amarillas,  sf.final_amarillas,
            sf.api_rojas,      sf.espn_rojas,      sf.ss_rojas,      sf.final_rojas,
            sf.api_var,        sf.espn_var,         sf.ss_var,        sf.final_var,
            sf.api_penales,    sf.espn_penales,    sf.ss_penales,    sf.final_penales,
            sf.api_minuto,     sf.espn_minuto,     sf.ss_minuto,     sf.minuto_primer_gol
        FROM partido_stats_fuentes sf
        WHERE sf.estado = 'finalizado'
        ORDER BY sf.numero_fifa::integer NULLS LAST
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    partidos = [dict(zip(cols, r)) for r in rows]

    total = len(partidos)
    print(f"\n{'='*70}")
    print(f"ANÁLISIS DE FUENTES — {total} partidos finalizados")
    print(f"{'='*70}\n")

    # ----------------------------------------------------------------
    # Estadísticas por fuente × campo
    # ----------------------------------------------------------------
    stats = {f: {c: {"match": 0, "diff": 0, "null": 0, "total_validos": 0,
                     "diffs": [], "errores": []}
                 for c in CAMPOS + ["minuto"]}
             for f in FUENTES}

    discrepancias = []

    for p in partidos:
        nf   = p["numero_fifa"] or "?"
        loc  = p["local"]
        vis  = p["visitante"]
        label = f"P{nf} {loc} vs {vis}"

        for campo in CAMPOS:
            final = p[f"final_{campo}"]
            if final is None:
                continue

            for fuente in FUENTES:
                val = p[f"{fuente}_{campo}"]
                st  = stats[fuente][campo]
                st["total_validos"] += 1

                if val is None:
                    st["null"] += 1
                elif val == final:
                    st["match"] += 1
                else:
                    st["diff"] += 1
                    diff = val - final
                    st["diffs"].append(diff)
                    st["errores"].append((label, val, final, diff))

        # Minuto primer gol
        final_min = p["minuto_primer_gol"]
        if final_min is not None:
            for fuente in FUENTES:
                val = p[f"{fuente}_minuto"]
                st  = stats[fuente]["minuto"]
                st["total_validos"] += 1
                if val is None:
                    st["null"] += 1
                elif val == final_min:
                    st["match"] += 1
                else:
                    st["diff"] += 1
                    diff = abs(val - final_min)
                    st["diffs"].append(diff)
                    st["errores"].append((label, val, final_min, val - final_min))

        # Detectar discrepancias entre fuentes (donde no todas coinciden)
        for campo in CAMPOS:
            vals = {f: p[f"{f}_{campo}"] for f in FUENTES}
            final = p[f"final_{campo}"]
            vals_notnull = {f: v for f, v in vals.items() if v is not None}
            if len(set(vals_notnull.values())) > 1:
                discrepancias.append({
                    "partido": label,
                    "campo": campo,
                    "final": final,
                    **{f"val_{f}": vals[f] for f in FUENTES},
                })

    # ----------------------------------------------------------------
    # Imprimir tabla resumen por campo
    # ----------------------------------------------------------------
    all_campos = CAMPOS + ["minuto"]
    campo_label = {"amarillas": "Amarillas (J)", "rojas": "Rojas (K)",
                   "var": "VAR (L)", "penales": "Penales (M)", "minuto": "Minuto gol (N)"}

    for campo in all_campos:
        print(f"{'─'*70}")
        print(f"  CAMPO: {campo_label[campo]}")
        print(f"{'─'*70}")
        print(f"  {'Fuente':<15} {'Válidos':>7} {'Match%':>8} {'Diff%':>8} {'Null%':>8} {'Error avg':>10}")
        print(f"  {'-'*55}")

        scores = {}
        for fuente in FUENTES:
            st = stats[fuente][campo]
            tot = st["total_validos"]
            if tot == 0:
                print(f"  {FUENTE_LABEL[fuente]:<15} {'N/A':>7}")
                continue

            match_pct = 100 * st["match"] / tot
            diff_pct  = 100 * st["diff"]  / tot
            null_pct  = 100 * st["null"]  / tot
            avg_err   = (sum(abs(d) for d in st["diffs"]) / len(st["diffs"])) if st["diffs"] else 0

            scores[fuente] = match_pct - null_pct * 0.5  # score compuesto

            marker = ""
            print(f"  {FUENTE_LABEL[fuente]:<15} {tot:>7} {match_pct:>7.1f}% {diff_pct:>7.1f}% "
                  f"{null_pct:>7.1f}% {avg_err:>10.2f}")

        if scores:
            mejor = max(scores, key=scores.get)
            print(f"  → Más confiable: {FUENTE_LABEL[mejor]}")
        print()

    # ----------------------------------------------------------------
    # Discrepancias entre fuentes
    # ----------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"DISCREPANCIAS ENTRE FUENTES ({len(discrepancias)} casos)")
    print(f"{'='*70}")
    for d in discrepancias[:30]:  # máximo 30
        api_v = d.get("val_api", "?")
        espn_v = d.get("val_espn", "?")
        ss_v   = d.get("val_ss", "?")
        final  = d["final"]
        print(f"  {d['partido']:40s} [{d['campo']:10s}]  "
              f"API={api_v}  ESPN={espn_v}  SS={ss_v}  FINAL={final}")
    if len(discrepancias) > 30:
        print(f"  ... y {len(discrepancias)-30} más")

    # ----------------------------------------------------------------
    # Ranking global de fuentes
    # ----------------------------------------------------------------
    print(f"\n{'='*70}")
    print("RANKING GLOBAL DE CONFIABILIDAD")
    print(f"{'='*70}")

    global_scores = {f: {"match": 0, "total": 0, "null": 0} for f in FUENTES}
    for campo in CAMPOS:  # solo campos con datos reales, excluir minuto por ahora
        for fuente in FUENTES:
            st = stats[fuente][campo]
            global_scores[fuente]["match"] += st["match"]
            global_scores[fuente]["total"] += st["total_validos"]
            global_scores[fuente]["null"]  += st["null"]

    ranking = []
    for fuente in FUENTES:
        gs = global_scores[fuente]
        if gs["total"] > 0:
            cobertura = 100 * (gs["total"] - gs["null"]) / gs["total"]
            precision = 100 * gs["match"] / max(gs["total"] - gs["null"], 1)
            score     = cobertura * 0.4 + precision * 0.6
            ranking.append((fuente, cobertura, precision, score))

    ranking.sort(key=lambda x: x[3], reverse=True)
    print(f"\n  {'Fuente':<15} {'Cobertura':>11} {'Precisión':>11} {'Score':>8}")
    print(f"  {'-'*50}")
    for i, (f, cob, prec, sc) in enumerate(ranking):
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
        print(f"  {medal} {FUENTE_LABEL[f]:<13} {cob:>10.1f}% {prec:>10.1f}% {sc:>8.1f}")

    print(f"\n  Nota: Score = Cobertura×0.4 + Precisión×0.6")
    print(f"  Cobertura = partidos donde la fuente devolvió datos (no null)")
    print(f"  Precisión = % de aciertos sobre los partidos con datos\n")

    conn.close()

if __name__ == "__main__":
    main()
