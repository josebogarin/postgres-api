"""
validar_bracket_oficial.py
==========================
Compara los standings y bracket R32 de la BD BECBUC contra los resultados
oficiales de la Copa del Mundo 2026.

Uso: python validar_bracket_oficial.py
"""

import asyncio
import asyncpg
from difflib import SequenceMatcher
import unicodedata
import sys, io
# Forzar UTF-8 en la consola de Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_DSN   = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2

# ─────────────────────────────────────────────────────────────────────────────
# VERDAD OFICIAL: deducida del bracket R32 confirmado por organización
# (usando armar_ronda32 para mapear BECBUC-letra → equipo esperado)
# ─────────────────────────────────────────────────────────────────────────────
# Grupo BECBUC → (1ro esperado, 2do esperado)
ESPERADO_GRUPOS = {
    "A": ("México",                        "Sudáfrica"),
    "B": ("España",                        "Canadá"),
    "C": ("Brasil",                        "Marruecos"),
    "D": ("Inglaterra",                    "Croacia"),
    "E": ("Alemania",                      "Costa de Marfil"),
    "F": ("Países Bajos",                  "Japón"),
    "G": ("Argentina",                     "Portugal"),
    "H": ("Colombia",                      "Senegal"),
    "I": ("Francia",                       "Noruega"),
    "J": ("Suiza",                         "Ghana"),
    "K": ("Bélgica",                       "Australia"),
    "L": ("Estados Unidos",                "Egipto"),
}

# R32 oficial (num_fifa, local, visitante)
CRUCES_OFICIALES = [
    (73, "Sudáfrica",                     "Canadá"),
    (74, "Alemania",                      "Paraguay"),
    (75, "Países Bajos",                  "Marruecos"),
    (76, "Brasil",                        "Japón"),
    (77, "Francia",                       "Suecia"),
    (78, "Costa de Marfil",               "Noruega"),
    (79, "México",                        "Ecuador"),
    (80, "Estados Unidos",                "Bosnia y Herzegovina"),
    (81, "Inglaterra",                    "República Democrática del Congo"),
    (82, "Argentina",                     "Cabo Verde"),
    (83, "Australia",                     "Egipto"),
    (84, "Colombia",                      "Ghana"),
    (85, "España",                        "Austria"),
    (86, "Suiza",                         "Senegal"),
    (87, "Bélgica",                       "Argelia"),
    (88, "Croacia",                       "Portugal"),
]

# Resultados finales oficiales de grupos (para verificar standings)
# (grupo_becbuc, equipo, pts, gd, gf)  — solo top2 de cada grupo
STANDINGS_OFICIALES = {
    "A": [("México",        9, +6), ("Sudáfrica",        4, -1)],
    "B": [("España",        7, +5), ("Canadá",           4, +5)],
    "C": [("Brasil",        7, +6), ("Marruecos",        7, +3)],
    "D": [("Inglaterra",    4, +2), ("Croacia",          3, -1)],
    "E": [("Alemania",      6, +6), ("Costa de Marfil",  6, +2)],
    "F": [("Países Bajos",  7, +6), ("Japón",            5, +4)],
    "G": [("Argentina",     6, +5), ("Portugal",         4, +5)],
    "H": [("Colombia",      6, +3), ("Senegal",          3, +0)],
    "I": [("Francia",       9, +8), ("Noruega",          6, +1)],
    "J": [("Suiza",         7, +4), ("Ghana",            4, +1)],
    "K": [("Bélgica",       5, +3), ("Australia",        4,  0)],
    "L": [("Estados Unidos", 6, +4), ("Egipto",          5, +2)],
}

# Alias de nombre
ALIAS = {
    "Países Bajos":                    ["Holanda", "Netherlands", "Paises Bajos", "Países Bajos"],
    "Costa de Marfil":                 ["Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"],
    "Bosnia y Herzegovina":            ["Bosnia", "Bosnia & Herzegovina", "Bosnia-Herzegovina"],
    "República Democrática del Congo": ["Congo DR", "RD Congo", "DR Congo", "Congo Rep. Dem.", "DRC"],
    "Cabo Verde":                      ["Cape Verde", "Cape Verde Islands", "Cabo Verde Islands"],
    "Estados Unidos":                  ["USA", "United States", "EE.UU.", "EEUU"],
    "Japón":                           ["Japan", "Japon"],
    "Marruecos":                       ["Morocco", "Maroc"],
    "Noruega":                         ["Norway"],
    "Suecia":                          ["Sweden"],
    "Sudáfrica":                       ["South Africa", "Sudafrica"],
    "Argelia":                         ["Algeria"],
    "Senegal":                         ["Sénégal"],
    "Bélgica":                         ["Belgium", "Belgique", "Belgica"],
    "Egipto":                          ["Egypt"],
    "Canadá":                          ["Canada"],
    "España":                          ["Spain", "Espana"],
    "Suiza":                           ["Switzerland"],
    "Colombia":                        ["Colombia"],
}


def normalize(name: str) -> str:
    n = unicodedata.normalize("NFD", name.lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn").strip()


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def matches(oficial: str, bd_nombre: str) -> bool:
    candidates = [oficial] + ALIAS.get(oficial, [])
    for c in candidates:
        if similar(c, bd_nombre) > 0.75:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────

VERDE  = "\033[92m"
ROJO   = "\033[91m"
AMARIL = "\033[93m"
CYAN   = "\033[96m"
BLANCO = "\033[97m"
GRIS   = "\033[90m"
RESET  = "\033[0m"


def ok(msg):   print(f"  {VERDE}✓ {msg}{RESET}")
def err(msg):  print(f"  {ROJO}✗ {msg}{RESET}")
def warn(msg): print(f"  {AMARIL}⚠ {msg}{RESET}")
def info(msg): print(f"  {GRIS}{msg}{RESET}")


async def main():
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}  VALIDACIÓN BECBUC vs OFICIAL — Copa del Mundo 2026{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    conn = await asyncpg.connect(DB_DSN)

    # ── 1. Estado partidos de grupos ─────────────────────────────────────────
    print(f"{BLANCO}1. ESTADO PARTIDOS DE GRUPOS{RESET}")
    grupos_rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa, p.estado, p.goles_local, p.goles_visitante,
               el.nombre AS local, ev.nombre AS visitante,
               f.nombre AS fase_nombre
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1 AND f.tipo ILIKE 'grupo%'
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    total = len(grupos_rows)
    finalizados = [r for r in grupos_rows if r["estado"] == "finalizado"]
    pendientes  = [r for r in grupos_rows if r["estado"] != "finalizado"]

    print(f"  Partidos de grupo: {len(finalizados)}/{total} finalizados")
    if pendientes:
        for p in pendientes:
            warn(f"P{p['numero_fifa']:03d} {p['local']} vs {p['visitante']} — estado: {p['estado']}")
    else:
        ok("Todos los partidos de grupo finalizados")

    # ── 2. Standings por grupo ────────────────────────────────────────────────
    print(f"\n{BLANCO}2. STANDINGS ACTUALES EN BD{RESET}")

    standings_rows = await conn.fetch("""
        SELECT
            fa.nombre AS grupo,
            e.nombre AS equipo,
            e.nombre_es,
            pa.pts AS puntos, pa.pj,
            pa.gf, pa.gc,
            (pa.gf - pa.gc) AS gd
        FROM participacion pa
        JOIN equipo e ON e.id = pa.equipo_id
        JOIN fase fa ON fa.id = pa.fase_id
        WHERE fa.torneo_id = $1 AND fa.tipo ILIKE 'grupo%'
        ORDER BY fa.nombre, pa.pts DESC, (pa.gf - pa.gc) DESC, pa.gf DESC
    """, TORNEO_ID)

    # Agrupar por fase
    from collections import defaultdict
    grupos = defaultdict(list)
    for r in standings_rows:
        # Extraer letra de grupo del nombre de fase ("Grupo A" → "A")
        gname = r["grupo"].strip()
        letra = gname[-1].upper() if gname else "?"
        grupos[letra].append(dict(r))

    errores_standings = []
    ok_standings = []

    for letra in sorted(grupos.keys()):
        equipos = grupos[letra]
        if not equipos:
            continue

        # Nombre BD (preferir nombre_es si existe)
        def nombre_bd(eq):
            return eq.get("nombre_es") or eq.get("equipo") or ""

        p1 = nombre_bd(equipos[0]) if len(equipos) > 0 else "?"
        p2 = nombre_bd(equipos[1]) if len(equipos) > 1 else "?"

        esp = ESPERADO_GRUPOS.get(letra)
        if not esp:
            info(f"Grupo {letra}: {p1} | {p2} — sin datos oficiales para comparar")
            continue

        esp1, esp2 = esp
        m1 = matches(esp1, nombre_bd(equipos[0])) if equipos else False
        m2 = matches(esp2, nombre_bd(equipos[1])) if len(equipos)>1 else False

        pts1 = equipos[0]["puntos"] if equipos else 0
        gd1  = equipos[0]["gd"]     if equipos else 0
        pts2 = equipos[1]["puntos"] if len(equipos)>1 else 0
        gd2  = equipos[1]["gd"]     if len(equipos)>1 else 0

        estado = ""
        if m1 and m2:
            estado = f"{VERDE}✓{RESET}"
            ok_standings.append(letra)
        else:
            estado = f"{ROJO}✗{RESET}"
            errores_standings.append(letra)

        # Mostrar tabla del grupo
        print(f"\n  {CYAN}Grupo {letra}{RESET}  {estado}")
        for i, eq in enumerate(equipos[:4], 1):
            nom = nombre_bd(eq)
            pos_marker = ""
            if i == 1:
                esperado_mark = f"  ← esperado: {esp1}"
                ok_1 = m1
            elif i == 2:
                esperado_mark = f"  ← esperado: {esp2}"
                ok_1 = m2
            else:
                esperado_mark = ""
                ok_1 = True

            col = VERDE if ok_1 or i > 2 else ROJO
            print(f"  {col}  {i}. {nom:<26} {eq['puntos']}pts  GD:{eq['gd']:+d}  GF:{eq['gf']}{esperado_mark}{RESET}")

    # ── 3. R32 Bracket en BD ─────────────────────────────────────────────────
    print(f"\n{BLANCO}3. BRACKET R32 (P73-P88){RESET}")

    r32_rows = await conn.fetch("""
        SELECT p.numero_fifa,
               el.nombre AS local, el.nombre_es AS local_es,
               ev.nombre AS visitante, ev.nombre_es AS visit_es,
               p.estado
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1 AND p.numero_fifa BETWEEN 73 AND 88
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    r32_map = {r["numero_fifa"]: dict(r) for r in r32_rows}

    errores_r32 = []
    ok_r32 = []

    for num, loc_oficial, vis_oficial in CRUCES_OFICIALES:
        p = r32_map.get(num)
        if not p:
            err(f"P{num:03d}: PARTIDO NO ENCONTRADO EN BD")
            errores_r32.append(num)
            continue

        loc_bd  = p.get("local_es")   or p.get("local")    or "TBD"
        vis_bd  = p.get("visit_es")   or p.get("visitante") or "TBD"

        m_loc = matches(loc_oficial, loc_bd)  if loc_bd != "TBD" else False
        m_vis = matches(vis_oficial, vis_bd)  if vis_bd != "TBD" else False

        if loc_bd == "TBD" or vis_bd == "TBD":
            estado_str = f"{AMARIL}⚠ TBD{RESET}"
            errores_r32.append(num)
        elif m_loc and m_vis:
            estado_str = f"{VERDE}✓{RESET}"
            ok_r32.append(num)
        else:
            estado_str = f"{ROJO}✗ DISCREPANCIA{RESET}"
            errores_r32.append(num)

        col_l = VERDE if m_loc else (ROJO if loc_bd != "TBD" else AMARIL)
        col_v = VERDE if m_vis else (ROJO if vis_bd != "TBD" else AMARIL)

        # Mostrar solo los problemáticos en detalle, los ok de forma compacta
        if m_loc and m_vis:
            print(f"  {VERDE}✓{RESET} P{num:<3} {loc_bd:<26} vs {vis_bd}")
        else:
            print(f"  {estado_str} P{num:<3}")
            print(f"       BD:      {col_l}{loc_bd:<26}{RESET} vs {col_v}{vis_bd}{RESET}")
            print(f"       OFICIAL: {loc_oficial:<26} vs {vis_oficial}")

    # ── 4. Resumen ────────────────────────────────────────────────────────────
    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}  RESUMEN{RESET}")
    print(f"{CYAN}{'='*70}{RESET}")

    grupos_ok = len(ok_standings)
    grupos_err = len(errores_standings)
    r32_ok = len(ok_r32)
    r32_err = len(errores_r32)

    col_g = VERDE if grupos_err == 0 else ROJO
    col_r = VERDE if r32_err == 0 else ROJO

    print(f"  Partidos finalizados:  {VERDE}{len(finalizados)}/{total}{RESET}")
    print(f"  Standings OK:          {col_g}{grupos_ok}/12 grupos{RESET}" +
          (f"  {ROJO}← errores en: {errores_standings}{RESET}" if errores_standings else ""))
    print(f"  R32 Bracket OK:        {col_r}{r32_ok}/16 partidos{RESET}" +
          (f"  {ROJO}← P{errores_r32} con problema{RESET}" if errores_r32 else ""))

    if grupos_err == 0 and r32_err == 0 and len(finalizados) == total:
        print(f"\n  {VERDE}✓✓✓ TODO VALIDADO — BD coincide con resultados oficiales ✓✓✓{RESET}")
    else:
        if len(pendientes) > 0:
            print(f"\n  {AMARIL}ACCIÓN: Hay {len(pendientes)} partido(s) sin finalizar en BD.{RESET}")
            print(f"  {AMARIL}         Ejecutar sincronizar_final_grupos.bat para sincronizar.{RESET}")
        if r32_err > 0:
            print(f"\n  {AMARIL}ACCIÓN: Ejecutar fix_r32_oficial.bat para corregir el bracket R32.{RESET}")
        if errores_standings:
            print(f"\n  {ROJO}ATENCIÓN: Standings de grupos {errores_standings} no coinciden con esperado.{RESET}")
            print(f"  {ROJO}         Verificar manualmente o re-sincronizar resultados.{RESET}")

    print(f"\n{CYAN}{'='*70}{RESET}\n")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
