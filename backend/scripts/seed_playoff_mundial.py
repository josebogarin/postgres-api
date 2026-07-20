"""
seed_playoff_mundial.py
=======================
Repara la base de datos `becbuc` para el torneo Mundial 2026 (torneo_id=2):

1. Reasigna los 24 partidos mal asignados a "Group Stage - 3" (fase id=31)
   al grupo correcto de cada equipo (vía tabla `participacion`).
2. Elimina fases vacías/espurias del torneo 2 (ids 19 y 31 si quedan vacías).
3. Crea las fases de playoff: r32, r16, qf, sf, tercer_puesto, final.
4. Inserta 32 partidos placeholder (equipos TBD) con fechas y ciudades del Excel.

Uso:
    & "C:\\proyecto FAST API\\backend\\.venv\\Scripts\\python.exe" `
      "C:\\proyecto FAST API\\backend\\scripts\\seed_playoff_mundial.py"
"""

import asyncio
import asyncpg
from datetime import datetime, time, date

DB_DSN = "postgresql://app_user:superpassword@localhost:5432/becbuc"

# Nota: fase NO tiene columna 'codigo' ni 'created_at'/'updated_at'
# partido usa 'fecha' (timestamptz), NOT 'fecha_hora'
# equipo_local_id / equipo_visitante_id son NOT NULL → se usa equipo TBD
TORNEO_ID = 2


# ---------------------------------------------------------------------------
# Datos de partidos playoff extraídos del Excel
# ---------------------------------------------------------------------------
PLAYOFF_FASES = [
    # (codigo, nombre, tipo, orden, visible_apostador)
    ("r32",          "Ronda de 32",       "ronda32",     15, True),
    ("r16",          "Octavos de Final",  "ronda16",     20, True),
    ("qf",           "Cuartos de Final",  "cuartos",     30, True),
    ("sf",           "Semifinales",       "semis",       40, True),
    ("tercer_puesto","Tercer Puesto",     "tercer_puesto",45, False),
    ("final",        "Final",             "final",       50, True),
]

# (num_excel, fecha, hora, ciudad, fase_codigo)
PARTIDOS_PLAYOFF = [
    # Ronda de 32 (#73-88)
    (73,  date(2026, 6, 28), time(15,  0), "Los Angeles",      "r32"),
    (74,  date(2026, 6, 29), time(13,  0), "Houston",          "r32"),
    (75,  date(2026, 6, 29), time(16, 30), "Boston",           "r32"),
    (76,  date(2026, 6, 29), time(21,  0), "Monterrey",        "r32"),
    (77,  date(2026, 6, 30), time(13,  0), "Dallas",           "r32"),
    (78,  date(2026, 6, 30), time(17,  0), "N. York/N. Jersey","r32"),
    (79,  date(2026, 6, 30), time(21,  0), "Ciudad de México", "r32"),
    (80,  date(2026, 7,  1), time(12,  0), "Atlanta",          "r32"),
    (81,  date(2026, 7,  1), time(16,  0), "Seattle",          "r32"),
    (82,  date(2026, 7,  1), time(20,  0), "San Francisco",    "r32"),
    (83,  date(2026, 7,  2), time(15,  0), "Los Angeles",      "r32"),
    (84,  date(2026, 7,  2), time(19,  0), "Toronto",          "r32"),
    (85,  date(2026, 7,  3), time(23,  0), "Vancouver",        "r32"),
    (86,  date(2026, 7,  3), time(14,  0), "Dallas",           "r32"),
    (87,  date(2026, 7,  3), time(18,  0), "Miami",            "r32"),
    (88,  date(2026, 7,  3), time(21, 30), "Kansas City",      "r32"),
    # Octavos de Final (#89-96)
    (89,  date(2026, 7,  4), time(13,  0), "Houston",          "r16"),
    (90,  date(2026, 7,  4), time(17,  0), "Filadelfia",       "r16"),
    (91,  date(2026, 7,  5), time(16,  0), "N. York/N. Jersey","r16"),
    (92,  date(2026, 7,  5), time(20,  0), "Ciudad de México", "r16"),
    (93,  date(2026, 7,  6), time(15,  0), "Dallas",           "r16"),
    (94,  date(2026, 7,  6), time(20,  0), "Seattle",          "r16"),
    (95,  date(2026, 7,  7), time(12,  0), "Atlanta",          "r16"),
    (96,  date(2026, 7,  7), time(16,  0), "Vancouver",        "r16"),
    # Cuartos de Final (#97-100)
    (97,  date(2026, 7,  9), time(16,  0), "Boston",           "qf"),
    (98,  date(2026, 7, 10), time(15,  0), "Los Angeles",      "qf"),
    (99,  date(2026, 7, 11), time(17,  0), "Miami",            "qf"),
    (100, date(2026, 7, 11), time(21,  0), "Kansas City",      "qf"),
    # Semifinales (#101-102)
    (101, date(2026, 7, 14), time(15,  0), "Dallas",           "sf"),
    (102, date(2026, 7, 15), time(15,  0), "Atlanta",          "sf"),
    # Tercer Puesto (#103)
    (103, date(2026, 7, 18), time(17,  0), "Miami",            "tercer_puesto"),
    # Final (#104)
    (104, date(2026, 7, 19), time(15,  0), "N. York/N. Jersey","final"),
]


async def main():
    conn = await asyncpg.connect(DB_DSN)
    try:
        async with conn.transaction():

            # ---------------------------------------------------------------
            # 1. Reparar fase de grupos: reasignar partidos de fase id=31
            # ---------------------------------------------------------------
            print("\n[1] Reasignando partidos mal asignados a 'Group Stage - 3' (fase_id=31)...")
            result = await conn.execute("""
                UPDATE partido p
                SET fase_id = (
                    SELECT pa.fase_id
                    FROM participacion pa
                    JOIN fase f ON f.id = pa.fase_id
                    WHERE pa.equipo_id IN (p.equipo_local_id, p.equipo_visitante_id)
                      AND f.torneo_id = $1
                      AND f.nombre LIKE 'Grupo %'
                    LIMIT 1
                )
                WHERE p.fase_id = 31
                  AND p.torneo_id = $1
            """, TORNEO_ID)
            print(f"   → {result}")

            # ---------------------------------------------------------------
            # 2. Eliminar fases vacías/espurias
            # ---------------------------------------------------------------
            print("\n[2] Eliminando fases vacías/espurias del torneo...")
            deleted = await conn.execute("""
                DELETE FROM fase
                WHERE torneo_id = $1
                  AND nombre NOT LIKE 'Grupo %'
                  AND tipo IN ('grupo', 'otro')
                  AND NOT EXISTS (
                      SELECT 1 FROM partido WHERE fase_id = fase.id
                  )
            """, TORNEO_ID)
            print(f"   → {deleted}")

            # Verificar estado grupos
            rows = await conn.fetch("""
                SELECT f.nombre, COUNT(p.id) AS partidos
                FROM fase f
                LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = $1
                WHERE f.torneo_id = $1
                GROUP BY f.id, f.nombre
                ORDER BY f.nombre
            """, TORNEO_ID)
            print("\n   Estado fases tras reparación:")
            ok = True
            for r in rows:
                estado = "✅" if r['partidos'] == 6 or r['partidos'] == 0 else "⚠️"
                if r['nombre'].startswith('Grupo') and r['partidos'] != 6:
                    ok = False
                print(f"   {estado} {r['nombre']}: {r['partidos']} partidos")
            if ok:
                print("   ✅ Todos los grupos tienen 6 partidos")

            # ---------------------------------------------------------------
            # 3. Crear fases de playoff
            # ---------------------------------------------------------------
            print("\n[3] Creando fases de playoff...")
            fase_id_map = {}
            for codigo, nombre, tipo, orden, visible in PLAYOFF_FASES:
                row = await conn.fetchrow("""
                    INSERT INTO fase (torneo_id, nombre, codigo, tipo, orden, visible_apostador,
                                     created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    ON CONFLICT (torneo_id, nombre) DO UPDATE
                        SET codigo = EXCLUDED.codigo,
                            tipo = EXCLUDED.tipo,
                            orden = EXCLUDED.orden,
                            visible_apostador = EXCLUDED.visible_apostador,
                            updated_at = NOW()
                    RETURNING id
                """, TORNEO_ID, nombre, codigo, tipo, orden, visible)
                fase_id_map[codigo] = row['id']
                print(f"   ✅ Fase '{nombre}' → id={row['id']}")

            # ---------------------------------------------------------------
            # 4. Insertar partidos playoff (placeholder, equipos TBD)
            # ---------------------------------------------------------------
            print("\n[4] Insertando partidos playoff...")
            inserted = 0
            skipped = 0
            for num, fecha, hora, ciudad, fase_codigo in PARTIDOS_PLAYOFF:
                fase_id = fase_id_map[fase_codigo]
                # Calcular fecha_hora combinando fecha y hora
                fecha_hora = datetime(fecha.year, fecha.month, fecha.day,
                                      hora.hour, hora.minute)
                # Insertar solo si no existe ya un partido con esa ciudad y fecha en esta fase
                existing = await conn.fetchval("""
                    SELECT id FROM partido
                    WHERE torneo_id = $1
                      AND fase_id = $2
                      AND fecha_hora = $3
                      AND ciudad = $4
                """, TORNEO_ID, fase_id, fecha_hora, ciudad)

                if existing:
                    print(f"   ↩️  #{num} ya existe (id={existing}), omitiendo")
                    skipped += 1
                    continue

                await conn.execute("""
                    INSERT INTO partido (
                        torneo_id, fase_id,
                        equipo_local_id, equipo_visitante_id,
                        fecha_hora, ciudad, estado,
                        created_at, updated_at
                    )
                    VALUES ($1, $2, NULL, NULL, $3, $4, 'programado', NOW(), NOW())
                """, TORNEO_ID, fase_id, fecha_hora, ciudad)
                print(f"   ✅ #{num} {fecha} {hora} | {ciudad} | {fase_codigo}")
                inserted += 1

            print(f"\n   → {inserted} partidos insertados, {skipped} omitidos")

            # ---------------------------------------------------------------
            # Resumen final
            # ---------------------------------------------------------------
            print("\n[Resumen final]")
            rows = await conn.fetch("""
                SELECT f.nombre, f.codigo, f.orden, COUNT(p.id) AS partidos
                FROM fase f
                LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = $1
                WHERE f.torneo_id = $1
                GROUP BY f.id, f.nombre, f.codigo, f.orden
                ORDER BY f.orden, f.nombre
            """, TORNEO_ID)
            for r in rows:
                print(f"   [{r['orden']:>3}] {r['nombre']:<25} ({r['codigo'] or '?':>15}): {r['partidos']} partidos")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
