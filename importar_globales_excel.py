"""
importar_globales_excel.py
Lee pronósticos globales (P111-P118) de la hoja '50- TBL MASTER' del Excel consolidado
y genera un SQL para importar (upsert) en apuesta_global.

Uso:
    python importar_globales_excel.py <ruta_excel>

Salida: importar_globales.sql  (ejecutar con docker exec)
"""

import sys
import os
import unicodedata
import openpyxl

HOJA      = "50- TBL MASTER"
TORNEO_ID = 2

P_MAP = {
    "P111": "campeon",
    "P112": "otro_finalista",
    "P113": "goleador",
    "P114": "peor_equipo",
    "P115": "etapa_paraguay",
    "P116": "goles_paraguay",
    "P117": "goleada_ganador",
    "P118": "goleada_perdedor",
}

FASE_NORM = {
    "grupo": "grupos", "grupos": "grupos",
    "16avos": "16avos", "dieciseisavos": "16avos",
    "8vos": "8vos", "octavos": "8vos",
    "4tos": "4tos", "cuartos": "4tos",
    "semi": "semis", "semifinal": "semis", "semis": "semis",
    "3p": "3p", "tercer puesto": "3p",
    "final": "final", "campeon": "final", "campeón": "final",
}

def norm(s):
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()

def limpiar_alias(v):
    if v is None: return ""
    return str(v).replace("\xa0", "").strip()

def esc(s):
    """Escapa string para SQL."""
    if s is None: return "NULL"
    return "'" + str(s).replace("'", "''").strip() + "'"

def leer_globales(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[HOJA]
    datos = {}  # {alias → {campo → valor}}
    for row in ws.iter_rows(values_only=True):
        pid = str(row[1]).strip() if row[1] else ""
        if pid not in P_MAP:
            continue
        campo = P_MAP[pid]
        alias = limpiar_alias(row[9])
        valor = row[10]
        if not alias or valor is None or str(valor).strip() == "":
            continue
        if alias not in datos:
            datos[alias] = {}
        datos[alias][campo] = str(valor).strip() if isinstance(valor, str) else valor
    wb.close()
    return datos

def generar_sql(globales, out_path):
    lines = []
    lines.append("-- importar_globales.sql")
    lines.append("-- Generado por importar_globales_excel.py")
    lines.append(f"-- Torneo ID: {TORNEO_ID}")
    lines.append("")
    lines.append("BEGIN;")
    lines.append("")

    # Header de referencia para ver aliases
    lines.append("-- ── Aliases encontrados en el Excel ──────────────────────────────────")
    for alias in sorted(globales.keys()):
        lines.append(f"-- {alias}")
    lines.append("")

    lines.append("-- ── Upsert apuesta_global por apostador ──────────────────────────────")
    lines.append("-- NOTA: apostador_id se resuelve por username en app_db.")
    lines.append("-- pred_campeon_id, pred_finalista_id, pred_peor_equipo_id se resuelven")
    lines.append("-- por nombre de equipo en becbuc.equipo.")
    lines.append("")

    for alias, d in sorted(globales.items()):
        campeon_nom    = d.get("campeon", "")
        finalista_nom  = d.get("otro_finalista", "")
        goleador       = d.get("goleador", "")
        peor_nom       = d.get("peor_equipo", "")
        etapa_raw      = d.get("etapa_paraguay", "")
        etapa_norm     = FASE_NORM.get(norm(etapa_raw), etapa_raw) if etapa_raw else ""
        goles_py       = d.get("goles_paraguay")
        goleada_gan    = d.get("goleada_ganador")
        goleada_per    = d.get("goleada_perdedor")

        lines.append(f"-- [{alias}]")
        lines.append(f"--   A-Campeon:    {campeon_nom}")
        lines.append(f"--   B-Finalista2: {finalista_nom}")
        lines.append(f"--   C-Goleador:   {goleador}")
        lines.append(f"--   D-Peor equipo:{peor_nom}")
        lines.append(f"--   E-Goleada:    {goleada_gan}-{goleada_per}")
        lines.append(f"--   F-Fase PY:    {etapa_raw} → {etapa_norm}")
        lines.append(f"--   G-Goles PY:   {goles_py}")

        # Sub-query para apostador_id (busca username = alias, case-insensitive)
        uid_q = f"(SELECT id FROM app_db.users WHERE lower(username) = lower({esc(alias)}) LIMIT 1)"

        # Sub-queries para equipo_id (busca por nombre, variantes)
        def equipo_q(nombre):
            if not nombre:
                return "NULL"
            n = nombre.strip().replace("'", "''")
            return (
                f"(SELECT id FROM equipo WHERE lower(nombre) LIKE lower('%{n}%') "
                f"OR lower(nombre) = lower('{n}') LIMIT 1)"
            )

        camp_q   = equipo_q(campeon_nom)
        fin2_q   = equipo_q(finalista_nom)
        peor_q   = equipo_q(peor_nom)

        goles_sql   = str(int(goles_py))   if goles_py   is not None else "NULL"
        gan_sql     = str(int(goleada_gan)) if goleada_gan is not None else "NULL"
        per_sql     = str(int(goleada_per)) if goleada_per is not None else "NULL"
        etapa_sql   = esc(etapa_norm)       if etapa_norm else "NULL"
        goleador_sql = esc(goleador)         if goleador   else "NULL"

        lines.append(f"""INSERT INTO apuesta_global
  (torneo_id, apostador_id,
   pred_campeon_id, pred_finalista1_id, pred_finalista2_id,
   pred_goleador, pred_peor_equipo_id,
   pred_goleada_ganador, pred_goleada_perdedor,
   pred_etapa_paraguay, pred_goles_paraguay)
SELECT
  {TORNEO_ID},
  {uid_q},
  {camp_q},
  {camp_q},
  {fin2_q},
  {goleador_sql},
  {peor_q},
  {gan_sql}, {per_sql},
  {etapa_sql}, {goles_sql}
WHERE {uid_q} IS NOT NULL
ON CONFLICT (torneo_id, apostador_id) DO UPDATE SET
  pred_campeon_id     = EXCLUDED.pred_campeon_id,
  pred_finalista1_id  = EXCLUDED.pred_finalista1_id,
  pred_finalista2_id  = EXCLUDED.pred_finalista2_id,
  pred_goleador       = EXCLUDED.pred_goleador,
  pred_peor_equipo_id = EXCLUDED.pred_peor_equipo_id,
  pred_goleada_ganador  = EXCLUDED.pred_goleada_ganador,
  pred_goleada_perdedor = EXCLUDED.pred_goleada_perdedor,
  pred_etapa_paraguay = EXCLUDED.pred_etapa_paraguay,
  pred_goles_paraguay = EXCLUDED.pred_goles_paraguay;
""")

    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- Verificación final:")
    lines.append(f"SELECT apostador_id, pred_campeon_id, pred_goleador, pred_etapa_paraguay, pred_goles_paraguay")
    lines.append(f"FROM apuesta_global WHERE torneo_id = {TORNEO_ID} ORDER BY apostador_id;")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"SQL generado: {out_path}")
    print(f"Apostadores procesados: {len(globales)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python importar_globales_excel.py <ruta_excel>")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"ERROR: No existe el archivo: {path}")
        sys.exit(1)

    out = os.path.join(os.path.dirname(path) or ".", "importar_globales.sql")
    globales = leer_globales(path)
    print(f"Apostadores con globales en Excel: {len(globales)}")
    generar_sql(globales, out)
    print(f"\nEjecutar con:")
    print(f'  Get-Content "{out}" | docker exec -i core-postgres psql -U app_user -d becbuc')
