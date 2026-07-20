"""
comparar_puntajes.py
Extrae puntajes de la BD BECBUC y compara contra tabla de referencia (imagen).
Ejecutar desde: cd "C:\proyecto FAST API" && python comparar_puntajes.py
"""
import subprocess
import sys
import os

# ---------------------------------------------------------------------------
# TABLA DE REFERENCIA extraida de la imagen (alias -> dict de columnas)
# Columnas imagen: A=resultado, B=marcador, C=amarillas, D=rojas, E=VAR, F=penales, G=minuto
# ---------------------------------------------------------------------------
REFERENCIA = {
    "SEBA":    {"A":152,"B":104,"C":14,"D":53,"E":27,"F":48,"G":2,  "TOTAL":400},
    "PATITO":  {"A":156,"B":48, "C":17,"D":57,"E":42,"F":56,"G":0,  "TOTAL":376},
    "MORO":    {"A":144,"B":80, "C":15,"D":45,"E":16,"F":56,"G":1,  "TOTAL":357},
    "VITRA":   {"A":128,"B":56, "C":15,"D":57,"E":42,"F":56,"G":2,  "TOTAL":356},
    "LAV":     {"A":156,"B":56, "C":15,"D":57,"E":12,"F":56,"G":0,  "TOTAL":352},
    "@BS":     {"A":152,"B":72, "C":2, "D":52,"E":24,"F":43,"G":1,  "TOTAL":346},
    "CHEREM":  {"A":136,"B":80, "C":12,"D":45,"E":12,"F":56,"G":2,  "TOTAL":343},
    "EZEQUIEL":{"A":152,"B":48, "C":12,"D":57,"E":17,"F":56,"G":1,  "TOTAL":343},
    "AERO":    {"A":132,"B":80, "C":13,"D":45,"E":12,"F":56,"G":0,  "TOTAL":338},
    "ANDRES":  {"A":140,"B":64, "C":15,"D":42,"E":16,"F":56,"G":1,  "TOTAL":334},
    "JUANCHO": {"A":132,"B":72, "C":14,"D":45,"E":12,"F":56,"G":2,  "TOTAL":333},
    "RODO":    {"A":152,"B":56, "C":11,"D":45,"E":12,"F":56,"G":0,  "TOTAL":332},
    "VALE":    {"A":136,"B":64, "C":13,"D":45,"E":16,"F":56,"G":2,  "TOTAL":332},
    "OSCAR":   {"A":124,"B":72, "C":14,"D":45,"E":16,"F":56,"G":2,  "TOTAL":329},
    "TITO":    {"A":144,"B":40, "C":14,"D":45,"E":12,"F":56,"G":1,  "TOTAL":312},
    "FATI":    {"A":120,"B":56, "C":13,"D":45,"E":12,"F":56,"G":1,  "TOTAL":303},
    "GERMAN":  {"A":128,"B":56, "C":10,"D":30,"E":12,"F":48,"G":1,  "TOTAL":285},
    "CUERVO":  {"A":120,"B":48, "C":11,"D":35,"E":16,"F":45,"G":1,  "TOTAL":276},
    "CHECHO":  {"A":128,"B":40, "C":9, "D":33,"E":6, "F":38,"G":1,  "TOTAL":255},
    "DIEGO":   {"A":120,"B":32, "C":7, "D":26,"E":6, "F":28,"G":0,  "TOTAL":219},
    # Agrega mas filas si la imagen tiene mas apostadores
    # Formato: "ALIAS": {"A":XX,"B":XX,"C":XX,"D":XX,"E":XX,"F":XX,"G":XX,"TOTAL":XX}
}

# ---------------------------------------------------------------------------
# Query a Docker PostgreSQL
# ---------------------------------------------------------------------------
QUERY = """
WITH base AS (
  SELECT
    ap.apostador_id,
    COALESCE(u.username, a.nombre_apostador, ap.apostador_id::text) AS alias,
    COALESCE(u.nombre, a.nombre_apostador, ap.apostador_id::text)   AS nombre_completo,
    COALESCE(SUM(pd.pts_resultado),0)::INT       AS H,
    COALESCE(SUM(pd.pts_marcador),0)::INT        AS I,
    COALESCE(SUM(pd.pts_amarillas),0)::INT       AS J,
    COALESCE(SUM(pd.pts_rojas),0)::INT           AS K,
    COALESCE(SUM(pd.pts_var),0)::INT             AS L,
    COALESCE(SUM(pd.pts_penales_partido),0)::INT AS M,
    COALESCE(SUM(pd.pts_minuto),0)::INT          AS N,
    COALESCE(SUM(pd.pts_penales_tanda),0)::INT   AS O,
    (COALESCE(SUM(pd.pts_resultado),0) +
     COALESCE(SUM(pd.pts_marcador),0) +
     COALESCE(SUM(pd.pts_amarillas),0) +
     COALESCE(SUM(pd.pts_rojas),0) +
     COALESCE(SUM(pd.pts_var),0) +
     COALESCE(SUM(pd.pts_penales_partido),0) +
     COALESCE(SUM(pd.pts_minuto),0) +
     COALESCE(SUM(pd.pts_penales_tanda),0))::INT AS TOTAL_PARTIDOS,
    COALESCE(pg.pts_campeon,0)+COALESCE(pg.pts_finalistas,0)+
    COALESCE(pg.pts_goleador,0)+COALESCE(pg.pts_peor_equipo,0)+
    COALESCE(pg.pts_mayor_goleada,0)+COALESCE(pg.pts_etapa_paraguay,0)+
    COALESCE(pg.pts_goles_paraguay,0) AS GLOBALES
  FROM (SELECT DISTINCT apostador_id FROM puntaje_detalle WHERE torneo_id = 2) ap
  LEFT JOIN puntaje_detalle pd ON pd.apostador_id = ap.apostador_id AND pd.torneo_id = 2
  LEFT JOIN (
      SELECT DISTINCT ON (apostador_id) apostador_id, nombre_apostador
      FROM apuesta
      ORDER BY apostador_id, id DESC
  ) a ON a.apostador_id = ap.apostador_id
  LEFT JOIN puntaje_global pg ON pg.apostador_id = ap.apostador_id AND pg.torneo_id = 2
  LEFT JOIN dblink('dbname=app_db user=app_user',
      'SELECT id, username, nombre FROM users'
  ) AS u(uid INT, username TEXT, nombre TEXT) ON u.uid = ap.apostador_id
  GROUP BY ap.apostador_id, u.username, u.nombre, a.nombre_apostador,
           pg.pts_campeon, pg.pts_finalistas,
           pg.pts_goleador, pg.pts_peor_equipo, pg.pts_mayor_goleada,
           pg.pts_etapa_paraguay, pg.pts_goles_paraguay
)
SELECT alias, nombre_completo, H, I, J, K, L, M, N, O, TOTAL_PARTIDOS, GLOBALES
FROM base
ORDER BY (TOTAL_PARTIDOS + GLOBALES) DESC;
"""

def run_query():
    cmd = [
        "docker", "exec", "core-postgres",
        "psql", "-U", "app_user", "-d", "becbuc",
        "-t", "-A", "-F", "|", "-c", QUERY
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print("ERROR Docker:", result.stderr)
            return []
        rows = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) < 12:
                continue
            rows.append({
                "alias":          parts[0].strip(),   # username de app_db
                "nombre_completo":parts[1].strip(),   # nombre de app_db
                "H":             int(parts[2] or 0),
                "I":             int(parts[3] or 0),
                "J":             int(parts[4] or 0),
                "K":             int(parts[5] or 0),
                "L":             int(parts[6] or 0),
                "M":             int(parts[7] or 0),
                "N":             int(parts[8] or 0),
                "O":             int(parts[9] or 0),
                "TOTAL_PARTIDOS":int(parts[10] or 0),
                "GLOBALES":      int(parts[11] or 0),
            })
        return rows
    except FileNotFoundError:
        print("ERROR: Docker no encontrado en PATH. Asegurate de que Docker Desktop esté corriendo.")
        return []
    except Exception as e:
        print(f"ERROR: {e}")
        return []


def normalize(name):
    """Normaliza alias para matching flexible."""
    return name.upper().strip().lstrip("@").replace(" ","").replace(".","")


def find_match(alias, bd_rows):
    """Busca la fila de BD que mejor coincide con el alias de referencia.
    Busca primero en username (alias), luego en nombre_completo."""
    na = normalize(alias)
    # Match exacto en username
    for row in bd_rows:
        if normalize(row["alias"]) == na:
            return row
    # Match exacto en nombre_completo
    for row in bd_rows:
        if normalize(row["nombre_completo"]) == na:
            return row
    # Match parcial en username
    for row in bd_rows:
        if na in normalize(row["alias"]) or normalize(row["alias"]) in na:
            return row
    # Match parcial en nombre_completo
    for row in bd_rows:
        nc = normalize(row["nombre_completo"])
        if na in nc or nc in na:
            return row
    return None


COL_MAP = {
    # imagen_col -> BD_col(s)
    # F es "penales" = M (penales partido) + O (penales tanda) combinados
    "A": "H",   # resultado
    "B": "I",   # marcador exacto
    "C": "J",   # amarillas
    "D": "K",   # rojas
    "E": "L",   # VAR
    "G": "N",   # minuto gol (acierto primer gol)
    # F se compara aparte como M+O
}


def main():
    print("=" * 70)
    print("COMPARACION PUNTAJES BECBUC vs TABLA REFERENCIA")
    print("=" * 70)

    print("\nConsultando BD...")
    bd_rows = run_query()

    if not bd_rows:
        print("\nNo se pudieron obtener datos de la BD.")
        print("Verificar: Docker corriendo, contenedor core-postgres activo.")
        return

    print(f"BD: {len(bd_rows)} apostadores con puntaje.")
    print(f"Referencia: {len(REFERENCIA)} apostadores en tabla imagen.\n")

    # Mostrar datos BD crudos
    print("--- DATOS BD (orden por total) ---")
    print(f"{'Username':<18} {'Nombre':<28} {'H':>5} {'I':>5} {'J':>5} {'K':>5} {'L':>5} {'M':>5} {'N':>5} {'O':>5} {'PART':>6} {'GLOB':>5} {'TOTAL':>6}")
    for r in bd_rows:
        total = r["TOTAL_PARTIDOS"] + r["GLOBALES"]
        print(f"{r['alias']:<18} {r['nombre_completo'][:27]:<28} {r['H']:>5} {r['I']:>5} {r['J']:>5} {r['K']:>5} {r['L']:>5} {r['M']:>5} {r['N']:>5} {r['O']:>5} {r['TOTAL_PARTIDOS']:>6} {r['GLOBALES']:>5} {total:>6}")

    print("\n--- DIFERENCIAS vs TABLA REFERENCIA ---")
    print(f"Nota: A=H(resultado) B=I(marcador) C=J(amar) D=K(rojas) E=L(VAR) F=M+O(penales) G=N(minuto)")
    print()

    diffs_found = False
    no_match = []

    for alias, ref in REFERENCIA.items():
        bd = find_match(alias, bd_rows)
        if bd is None:
            no_match.append(alias)
            continue

        bd_total_partidos = bd["TOTAL_PARTIDOS"]
        bd_total = bd["TOTAL_PARTIDOS"] + bd["GLOBALES"]

        # Comparar cada columna simple
        item_diffs = []
        for img_col, bd_col in COL_MAP.items():
            img_val = ref.get(img_col, 0)
            bd_val = bd.get(bd_col, 0)
            if img_val != bd_val:
                item_diffs.append(f"  {img_col}({bd_col}): imagen={img_val} BD={bd_val} (diff={bd_val-img_val:+d})")

        # F = M + O (penales partido + penales tanda)
        img_f = ref.get("F", 0)
        bd_f = bd.get("M", 0) + bd.get("O", 0)
        if img_f != bd_f:
            item_diffs.append(f"  F(M+O): imagen={img_f} BD={bd_f} [M={bd['M']} O={bd['O']}] (diff={bd_f-img_f:+d})")

        ref_total = ref.get("TOTAL", 0)

        if item_diffs:
            diffs_found = True
            print(f"[{alias}] (BD user: {bd['alias']} / {bd['nombre_completo']})")
            print(f"  Imagen total={ref_total}  BD partidos={bd_total_partidos}  BD total(+glob)={bd_total}")
            for d in item_diffs:
                print(d)
            print()
        else:
            print(f"[{alias}] OK ({bd['alias']} / {bd['nombre_completo']}) - partidos coinciden")

    if no_match:
        print(f"\nSin match en BD: {', '.join(no_match)}")
        print("Verificar nombres en REFERENCIA dict o en BD.")

    if not diffs_found and not no_match:
        print("\n✅ Todos los puntajes coinciden con la tabla de referencia.")

    # Guardar CSV BD
    csv_path = r"C:\proyecto FAST API\becbuc_scores.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("username|nombre_completo|H|I|J|K|L|M|N|O|TOTAL_PARTIDOS|GLOBALES|TOTAL\n")
        for r in bd_rows:
            total = r["TOTAL_PARTIDOS"] + r["GLOBALES"]
            f.write(f"{r['alias']}|{r['nombre_completo']}|{r['H']}|{r['I']}|{r['J']}|{r['K']}|{r['L']}|{r['M']}|{r['N']}|{r['O']}|{r['TOTAL_PARTIDOS']}|{r['GLOBALES']}|{total}\n")
    print(f"\nCSV guardado: {csv_path}")


if __name__ == "__main__":
    main()
