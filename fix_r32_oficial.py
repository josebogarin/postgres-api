"""
fix_r32_oficial.py
==================
Verifica los cruces oficiales R32 contra la BD y los actualiza si hay discrepancias.
Uso: python fix_r32_oficial.py
"""

import asyncio
import asyncpg
from difflib import SequenceMatcher

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"
TORNEO_ID = 2

# Cruces oficiales en orden P73-P88
# Fuente: lavoz.com.ar (confirmados por organizacion)
CRUCES_OFICIALES = [
    # (num, local, visitante)
    (73,  "Sudáfrica",                    "Canadá"),
    (74,  "Alemania",                     "Paraguay"),
    (75,  "Países Bajos",                 "Marruecos"),
    (76,  "Brasil",                       "Japón"),
    (77,  "Francia",                      "Suecia"),
    (78,  "Costa de Marfil",              "Noruega"),
    (79,  "México",                       "Ecuador"),
    (80,  "Estados Unidos",               "Bosnia y Herzegovina"),
    (81,  "Inglaterra",                   "República Democrática del Congo"),
    (82,  "Argentina",                    "Cabo Verde"),
    (83,  "Australia",                    "Egipto"),
    (84,  "Colombia",                     "Ghana"),
    (85,  "España",                       "Austria"),
    (86,  "Suiza",                        "Senegal"),
    (87,  "Bélgica",                      "Argelia"),
    (88,  "Croacia",                      "Portugal"),
]

# Alias para nombres que pueden variar en la BD
ALIAS = {
    "Países Bajos":                   ["Holanda", "Netherlands", "Paises Bajos", "Países Bajos"],
    "Costa de Marfil":                ["Ivory Coast", "Côte d'Ivoire", "Cote d'Ivoire"],
    "Bosnia y Herzegovina":           ["Bosnia", "Bosnia & Herzegovina", "Bosnia-Herzegovina"],
    "República Democrática del Congo":["Congo DR", "RD Congo", "DR Congo", "Congo, Rep. Dem.", "DRC", "Congo Rep. Dem.", "Rep. Democratica del Congo"],
    "Cabo Verde":                     ["Cape Verde"],
    "Estados Unidos":                 ["USA", "United States", "EE.UU.", "EEUU"],
    "Japón":                          ["Japan", "Japon"],
    "Marruecos":                      ["Morocco", "Maroc"],
    "Noruega":                        ["Norway", "Norvège"],
    "Suecia":                         ["Sweden", "Suède"],
    "Sudáfrica":                      ["South Africa", "Sudafrica"],
    "Argelia":                        ["Algeria"],
    "Senegal":                        ["Sénégal"],
    "Bélgica":                        ["Belgium", "Belgique", "Belgica"],
    "Egipto":                         ["Egypt"],
    "Canadá":                         ["Canada"],
    "España":                         ["Spain", "Espana"],
    "Suiza":                          ["Switzerland"],
    "Colombia":                       ["Colombia"],
    "Austria":                        ["Osterreich", "Österreich"],
    "Ghana":                          ["Ghana"],
    "Croacia":                        ["Croatia", "Croatie"],
    "Portugal":                       ["Portugal"],
    "Australia":                      ["Australia"],
    "Inglaterra":                     ["England", "Angleterre"],
    "Alemania":                       ["Germany", "Deutschland", "Allemagne"],
    "Brasil":                         ["Brazil", "Brésil"],
    "Francia":                        ["France"],
    "México":                         ["Mexico"],
    "Argentina":                      ["Argentina"],
    "Paraguay":                       ["Paraguay"],
    "Ecuador":                        ["Ecuador"],
}


def normalize(name: str) -> str:
    import unicodedata
    n = unicodedata.normalize("NFD", name.lower())
    return "".join(c for c in n if unicodedata.category(c) != "Mn").strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def find_best_match(target: str, equipos: list[dict]) -> dict | None:
    """Encuentra el equipo en la BD que mejor coincide con el nombre."""
    candidates = [target] + ALIAS.get(target, [])
    best_score = 0.0
    best_eq = None
    for eq in equipos:
        for name in [eq.get("nombre", ""), eq.get("nombre_es", "") or ""]:
            if not name:
                continue
            for cand in candidates:
                s = similarity(cand, name)
                if s > best_score:
                    best_score = s
                    best_eq = eq
    return best_eq if best_score > 0.6 else None


async def main():
    print("Conectando a BD becbuc...")
    conn = await asyncpg.connect(DB_DSN)

    # 1. Cargar todos los equipos
    rows = await conn.fetch("SELECT id, nombre, nombre_es FROM equipo ORDER BY nombre")
    equipos = [dict(r) for r in rows]
    print(f"  {len(equipos)} equipos en BD\n")

    # 2. Cargar partidos R32 actuales (numero_fifa 73-88)
    r32_rows = await conn.fetch("""
        SELECT p.id, p.numero_fifa,
               el.nombre AS local_nombre, el.nombre_es AS local_nombre_es,
               ev.nombre AS visit_nombre, ev.nombre_es AS visit_nombre_es,
               p.equipo_local_id, p.equipo_visitante_id,
               p.estado
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = $1 AND p.numero_fifa BETWEEN 73 AND 88
        ORDER BY p.numero_fifa
    """, TORNEO_ID)

    r32_map = {r["numero_fifa"]: dict(r) for r in r32_rows}
    print(f"  {len(r32_map)} partidos R32 encontrados en BD\n")

    # 3. Comparar y actualizar
    print("=" * 70)
    print(f"{'NUM':<5} {'OFICIAL LOCAL':<28} {'OFICIAL VISITANTE':<28} ESTADO")
    print("=" * 70)

    updates = []
    errors = []

    for num, local_oficial, visit_oficial in CRUCES_OFICIALES:
        partido = r32_map.get(num)
        if not partido:
            print(f"P{num:<3} *** PARTIDO NO ENCONTRADO EN BD ***")
            errors.append(f"P{num}: partido no existe en BD")
            continue

        estado = partido["estado"] or "pendiente"
        local_bd = partido.get("local_nombre_es") or partido.get("local_nombre") or "TBD"
        visit_bd = partido.get("visit_nombre_es") or partido.get("visit_nombre") or "TBD"

        # Verificar si ya coincide
        local_match = find_best_match(local_oficial, equipos)
        visit_match = find_best_match(visit_oficial, equipos)

        local_ok = (local_match and partido["equipo_local_id"] == local_match["id"])
        visit_ok = (visit_match and partido["equipo_visitante_id"] == visit_match["id"])

        if local_ok and visit_ok:
            status = "✓ OK"
        elif estado == "finalizado":
            status = "⚠ FINALIZADO (no se toca)"
            local_ok = True
            visit_ok = True
        else:
            status = "✗ ACTUALIZAR"

        print(f"P{num:<3} {local_oficial:<28} vs {visit_oficial:<28} | BD: {local_bd} vs {visit_bd} | {status}")

        if not (local_ok and visit_ok) and estado != "finalizado":
            if local_match and visit_match:
                updates.append({
                    "partido_id": partido["id"],
                    "num": num,
                    "local_id": local_match["id"],
                    "visit_id": visit_match["id"],
                    "local_nombre": local_oficial,
                    "visit_nombre": visit_oficial,
                })
            else:
                if not local_match:
                    errors.append(f"P{num}: no se encontró equipo '{local_oficial}' en BD")
                if not visit_match:
                    errors.append(f"P{num}: no se encontró equipo '{visit_oficial}' en BD")

    print("=" * 70)

    if errors:
        print(f"\nERRORES ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")

    if not updates:
        print("\nOK Bracket R32 ya coincide con los cruces oficiales.")
    else:
        print(f"\n-> {len(updates)} partido(s) necesitan actualizarse:")
        for u in updates:
            print(f"  P{u['num']}: {u['local_nombre']} vs {u['visit_nombre']} (partido_id={u['partido_id']})")

        confirm = input("\nAplicar cambios? (s/n): ").strip().lower()
        if confirm == "s":
            async with conn.transaction():
                for u in updates:
                    await conn.execute("""
                        UPDATE partido
                        SET equipo_local_id    = $1,
                            equipo_visitante_id = $2
                        WHERE id = $3
                    """, u["local_id"], u["visit_id"], u["partido_id"])
                    print(f"  OK P{u['num']} actualizado")
            print("\nOK BD actualizada.")

            # Notificar al backend para sincronizar bracket
            import urllib.request, json as _json
            try:
                print("\nNOTA: No se llama avanzar-bracket para no sobreescribir los cruces.")
                print("      Ejecutar calcular-puntajes manualmente desde el portal.")
            except Exception as e:
                print(f"  WARN API: {e}")
                print("  Hacé clic en 'Avanzar bracket' y 'Calcular puntajes' desde el portal.")
        else:
            print("  Cancelado, sin cambios.")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
