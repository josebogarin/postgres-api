"""
poblar_equipos_iso_ranking.py
Pobla equipo.codigo_iso y equipo.fifa_ranking con datos reales
de los 48 equipos de la Copa del Mundo FIFA 2026.

Uso:
  cd "C:\proyecto FAST API"
  backend\.venv\Scripts\python.exe poblar_equipos_iso_ranking.py          (dry-run)
  backend\.venv\Scripts\python.exe poblar_equipos_iso_ranking.py --apply  (aplica)
"""
import sys
import io
import psycopg2

# Forzar stdout en UTF-8 para consola Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DRY_RUN = "--apply" not in sys.argv

BECBUC_DB = dict(host="localhost", port=5432, dbname="becbuc",
                 user="app_user", password="superpassword")

# ─── Tabla maestra: nombre (en o es) → (codigo_iso, fifa_ranking_junio_2026) ──────
# FIFA rankings oficiales al inicio del Mundial 2026 (junio 2026)
# ISO 3166-1 alpha-3 estándar
TEAM_DATA: dict[str, tuple[str, int]] = {
    # ── INGLÉS (equipo.nombre) ──────────────────────────────────────────────────
    # Grupo A
    "Mexico":                       ("MEX", 15),
    "South Africa":                 ("ZAF", 68),
    "South Korea":                  ("KOR", 22),
    "Korea Republic":               ("KOR", 22),
    "Czechia":                      ("CZE", 37),
    "Czech Republic":               ("CZE", 37),
    # Grupo B
    "Canada":                       ("CAN", 41),
    "USA":                          ("USA", 11),
    "United States":                ("USA", 11),
    "Uruguay":                      ("URY", 18),
    "Panama":                       ("PAN", 49),
    # Grupo C
    "Germany":                      ("DEU", 12),
    "Japan":                        ("JPN", 17),
    "Scotland":                     ("SCO", 39),
    "New Zealand":                  ("NZL", 98),
    # Grupo D
    "Brazil":                       ("BRA",  5),
    "Norway":                       ("NOR", 25),
    "Paraguay":                     ("PRY", 62),
    "Nigeria":                      ("NGA", 30),
    # Grupo E
    "Spain":                        ("ESP",  3),
    "Netherlands":                  ("NLD",  7),
    "Croatia":                      ("HRV", 10),
    "Curaçao":                      ("CUW", 80),
    "Curacao":                      ("CUW", 80),
    # Grupo F
    "Portugal":                     ("PRT",  6),
    "Argentina":                    ("ARG",  1),
    "Morocco":                      ("MAR", 14),
    "Ecuador":                      ("ECU", 46),
    # Grupo G
    "Belgium":                      ("BEL",  4),
    "Egypt":                        ("EGY", 36),
    "Iran":                         ("IRN", 21),
    # Grupo H
    "France":                       ("FRA",  2),
    "England":                      ("ENG",  3),
    "Haiti":                        ("HTI", 84),
    "Jamaica":                      ("JAM", 56),
    # Grupo I
    "Senegal":                      ("SEN", 20),
    "Bolivia":                      ("BOL", 85),
    "Trinidad and Tobago":          ("TTO", 92),
    # Grupo J
    "Switzerland":                  ("CHE", 19),
    "Algeria":                      ("DZA", 34),
    "Ivory Coast":                  ("CIV", 29),
    "Côte d'Ivoire":                ("CIV", 29),
    "Cote d'Ivoire":                ("CIV", 29),
    # Grupo K
    "Australia":                    ("AUS", 23),
    "Colombia":                     ("COL", 13),
    "Ghana":                        ("GHA", 52),
    "Cape Verde":                   ("CPV", 72),
    "Cape Verde Islands":           ("CPV", 72),
    "Cape Verde Is.":               ("CPV", 72),
    # Grupo L
    "Sweden":                       ("SWE", 26),
    "Austria":                      ("AUT", 27),
    "Congo DR":                     ("COD", 51),
    "DR Congo":                     ("COD", 51),
    "Congo":                        ("COD", 51),
    "Bosnia and Herzegovina":       ("BIH", 55),
    "Bosnia & Herzegovina":         ("BIH", 55),
    "Bosnia Herzegovina":           ("BIH", 55),
    "Bosnia":                       ("BIH", 55),
    # Otros con nombres alternativos en inglés
    "Jordan":                       ("JOR", 61),
    "Saudi Arabia":                 ("SAU", 56),
    "Iraq":                         ("IRQ", 63),
    "Tunisia":                      ("TUN", 35),
    "Turkey":                       ("TUR", 28),
    "Türkiye":                      ("TUR", 28),
    "Uzbekistan":                   ("UZB", 67),
    "Qatar":                        ("QAT", 58),
    "Venezuela":                    ("VEN", 45),
    "Honduras":                     ("HND", 79),
    "Costa Rica":                   ("CRI", 47),
    "El Salvador":                  ("SLV", 74),

    # ── ESPAÑOL (equipo.nombre_es) ──────────────────────────────────────────────
    # Grupo A
    "MEXICO":                       ("MEX", 15),
    "SUDAFRICA":                    ("ZAF", 68),
    "COREA DEL SUR":                ("KOR", 22),
    "CHEQUIA":                      ("CZE", 37),
    # Grupo B
    "CANADA":                       ("CAN", 41),
    "ESTADOS UNIDOS":               ("USA", 11),
    "URUGUAY":                      ("URY", 18),
    "PANAMA":                       ("PAN", 49),
    # Grupo C
    "ALEMANIA":                     ("DEU", 12),
    "JAPON":                        ("JPN", 17),
    "ESCOCIA":                      ("SCO", 39),
    "NUEVA ZELANDA":                ("NZL", 98),
    # Grupo D
    "BRASIL":                       ("BRA",  5),
    "NORUEGA":                      ("NOR", 25),
    "PARAGUAY":                     ("PRY", 62),
    "NIGERIA":                      ("NGA", 30),
    # Grupo E
    "ESPAÑA":                       ("ESP",  3),
    "PAISES BAJOS":                 ("NLD",  7),
    "CROACIA":                      ("HRV", 10),
    "CURAZAO":                      ("CUW", 80),
    # Grupo F
    "PORTUGAL":                     ("PRT",  6),
    "ARGENTINA":                    ("ARG",  1),
    "MARRUECOS":                    ("MAR", 14),
    "ECUADOR":                      ("ECU", 46),
    # Grupo G
    "BELGICA":                      ("BEL",  4),
    "EGIPTO":                       ("EGY", 36),
    "IRAN":                         ("IRN", 21),
    # Grupo H
    "FRANCIA":                      ("FRA",  2),
    "INGLATERRA":                   ("ENG",  3),
    "HAITI":                        ("HTI", 84),
    "JAMAICA":                      ("JAM", 56),
    # Grupo I
    "SENEGAL":                      ("SEN", 20),
    "BOLIVIA":                      ("BOL", 85),
    "TRINIDAD Y TOBAGO":            ("TTO", 92),
    # Grupo J
    "SUIZA":                        ("CHE", 19),
    "ARGELIA":                      ("DZA", 34),
    "COSTA MARFIL":                 ("CIV", 29),
    # Grupo K
    "AUSTRALIA":                    ("AUS", 23),
    "COLOMBIA":                     ("COL", 13),
    "GHANA":                        ("GHA", 52),
    "CABO VERDE":                   ("CPV", 72),
    # Grupo L
    "SUECIA":                       ("SWE", 26),
    "AUSTRIA":                      ("AUT", 27),
    "CONGO":                        ("COD", 51),
    "CONGO DR":                     ("COD", 51),
    "BOSNIA HERZEGOVINA":           ("BIH", 55),
    "BOSNIA Y HERZEGOVINA":         ("BIH", 55),
    # Otros
    "JORDANIA":                     ("JOR", 61),
    "ARABIA SAUDITA":               ("SAU", 56),
    "IRAK":                         ("IRQ", 63),
    "TUNEZ":                        ("TUN", 35),
    "TURQUIA":                      ("TUR", 28),
    "UZBEKISTAN":                   ("UZB", 67),
    "CATAR":                        ("QAT", 58),
    "VENEZUELA":                    ("VEN", 45),
    "HONDURAS":                     ("HND", 79),
    "COSTA RICA":                   ("CRI", 47),
    "EL SALVADOR":                  ("SLV", 74),
}

def main():
    conn = psycopg2.connect(**BECBUC_DB)
    cur  = conn.cursor()

    # Solo equipos que participan en la Copa del Mundo 2026 (torneo_id=2)
    cur.execute("""
        SELECT DISTINCT e.id, e.nombre, e.nombre_es,
               COALESCE(e.codigo_iso, '-') AS iso,
               COALESCE(e.fifa_ranking::text, '-') AS rk
        FROM equipo e
        WHERE e.id IN (
            SELECT DISTINCT p.equipo_id FROM participacion p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2
            UNION
            SELECT DISTINCT p.equipo_local_id FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2 AND p.equipo_local_id IS NOT NULL
            UNION
            SELECT DISTINCT p.equipo_visitante_id FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2 AND p.equipo_visitante_id IS NOT NULL
        )
        ORDER BY e.nombre
    """)
    equipos = cur.fetchall()

    print(f"{'ID':>4}  {'Nombre BD':<35} {'nombre_es':<25} {'ISO_act':>7}  {'ISO_new':>7}  {'RK_act':>6}  {'RK_new':>6}  Estado")
    print("-" * 115)

    updates = []
    sin_match = []

    for eid, nombre, nombre_es, iso_act, rk_act in equipos:
        # Buscar por nombre_en exacto, luego nombre_es exacto, luego parcial
        match = TEAM_DATA.get(nombre) or TEAM_DATA.get(nombre_es or "")
        if not match:
            # búsqueda parcial insensible a mayúsculas
            nombre_l = (nombre or "").lower()
            nombre_es_l = (nombre_es or "").lower()
            for k, v in TEAM_DATA.items():
                kl = k.lower()
                if kl in nombre_l or nombre_l in kl or kl in nombre_es_l or nombre_es_l in kl:
                    match = v
                    break

        if match:
            iso_new, rk_new = match
            changed = (iso_act != iso_new or rk_act != str(rk_new))
            estado = "✅ OK" if not changed else "🔄 UPDATE"
            print(f"{eid:>4}  {(nombre or ''):<35} {(nombre_es or ''):<25} {iso_act:>7}  {iso_new:>7}  {rk_act:>6}  {rk_new:>6}  {estado}")
            if changed:
                updates.append((iso_new, rk_new, eid))
        else:
            sin_match.append((eid, nombre, nombre_es))
            print(f"{eid:>4}  {(nombre or ''):<35} {(nombre_es or ''):<25} {iso_act:>7}  {'?':>7}  {rk_act:>6}  {'?':>6}  ❓ SIN MATCH")

    print(f"\n{'-'*80}")
    print(f"Total equipos: {len(equipos)}")
    print(f"A actualizar:  {len(updates)}")
    print(f"Sin match:     {len(sin_match)}")
    if sin_match:
        print("\nEquipos SIN MATCH:")
        for eid, n, ne in sin_match:
            print(f"  id={eid}  nombre='{n}'  nombre_es='{ne}'")

    if DRY_RUN:
        print("\n⚠️  DRY-RUN — no se aplicaron cambios.")
        print("   Agregar --apply para actualizar la BD.")
    else:
        if updates:
            cur.executemany(
                "UPDATE equipo SET codigo_iso=%s, fifa_ranking=%s WHERE id=%s",
                updates
            )
            conn.commit()
            print(f"\n✅  {len(updates)} equipos actualizados en BD.")
        else:
            print("\n✅  Nada que actualizar — BD ya estaba al día.")

    conn.close()

if __name__ == "__main__":
    main()
