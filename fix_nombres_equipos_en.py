"""
fix_nombres_equipos_en.py
=========================
Actualiza nombres de equipos en espanol/mayusculas a ingles estandar en la BD becbuc.
Campo: equipo.nombre (ingles) / equipo.nombre_es (espanol, se preserva)
"""
import asyncio
import asyncpg
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"

# nombre_actual -> nombre_en_ingles
FIXES = {
    # Equipos en espanol/mayusculas encontrados en BD
    "ALEMANIA":               "Germany",
    "COSTA DE MARFIL":        "Ivory Coast",
    "BOSNIA Y HERZEGOVINA":   "Bosnia & Herzegovina",
    "COREA DEL SUR":          "South Korea",
    "INGLATERRA":             "England",
    # Otros posibles
    "PAISES BAJOS":           "Netherlands",
    "ESTADOS UNIDOS":         "United States",
    "SUIZA":                  "Switzerland",
    "BELGICA":                "Belgium",
    "ESPANA":                 "Spain",
    "BRASIL":                 "Brazil",
    "FRANCIA":                "France",
    "ALEMANIA":               "Germany",
    "JAPON":                  "Japan",
    "NORUEGA":                "Norway",
    "SUECIA":                 "Sweden",
    "SUDAFRICA":              "South Africa",
    "ARGELIA":                "Algeria",
    "MARRUECOS":              "Morocco",
    "EGIPTO":                 "Egypt",
    "CROACIA":                "Croatia",
    "CANADA":                 "Canada",
    "MEXICO":                 "Mexico",
    "ECUADOR":                "Ecuador",
    "ARGENTINA":              "Argentina",
    "COLOMBIA":               "Colombia",
    "PARAGUAY":               "Paraguay",
    "PORTUGAL":               "Portugal",
    "AUSTRIA":                "Austria",
    "GHANA":                  "Ghana",
    "AUSTRALIA":              "Australia",
    "CAPE VERDE":             "Cape Verde Islands",
    "CABO VERDE":             "Cape Verde Islands",
    "REPUBLICA DEMOCRATICA DEL CONGO": "Congo DR",
    "SENEGAL":                "Senegal",
    "JAPON":                  "Japan",
    "TURQUIA":                "Turkey",
}

async def main():
    conn = await asyncpg.connect(DB_DSN)

    # 1. Mostrar todos los equipos actuales
    rows = await conn.fetch("SELECT id, nombre, nombre_es FROM equipo ORDER BY nombre")
    print(f"Total equipos en BD: {len(rows)}\n")

    # 2. Detectar candidatos a corregir
    to_fix = []
    for r in rows:
        nom = r['nombre'] or ''
        # Detectar: todo mayusculas, o matchea alguna clave del FIXES
        clave = nom.strip().upper()
        clave_norm = clave.replace('Á','A').replace('É','E').replace('Í','I').replace('Ó','O').replace('Ú','U').replace('Ñ','N')
        new_name = FIXES.get(nom.strip()) or FIXES.get(clave) or FIXES.get(clave_norm)
        if new_name and new_name != nom.strip():
            to_fix.append({'id': r['id'], 'old': nom, 'new': new_name, 'nombre_es': r['nombre_es']})

    if not to_fix:
        print("No se encontraron equipos con nombres en espanol para corregir.")
        await conn.close()
        return

    print(f"Equipos a corregir ({len(to_fix)}):")
    for f in to_fix:
        es = f['nombre_es'] or ''
        print(f"  id={f['id']:<5} '{f['old']}'  ->  '{f['new']}'  (nombre_es: {es})")

    print()
    confirm = input("Aplicar cambios? (s/n): ").strip().lower()
    if confirm != 's':
        print("Cancelado.")
        await conn.close()
        return

    async with conn.transaction():
        for f in to_fix:
            # Preservar nombre_es si esta vacio y el nombre viejo era espanol
            new_es = f['nombre_es']
            if not new_es:
                new_es = f['old']  # guardar el nombre espanol en nombre_es
            await conn.execute(
                "UPDATE equipo SET nombre = $1, nombre_es = $2 WHERE id = $3",
                f['new'], new_es, f['id']
            )
            print(f"  OK id={f['id']}: '{f['old']}' -> '{f['new']}'")

    print(f"\nOK {len(to_fix)} equipos actualizados.")
    print("Nota: ejecutar calcular-puntajes desde el portal para refrescar scores.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
