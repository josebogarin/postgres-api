"""
Diagnostico y fix de goles Paraguay en BD.
Ejecutar: cd "C:\proyecto FAST API\backend" && .venv\Scripts\python.exe ..\diagnostico_paraguay_goles.py
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://app_user@localhost:5432/becbuc"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        r = await conn.execute(text("""
            SELECT p.id, p.numero_fifa,
                   eq_l.nombre AS local, p.goles_local,
                   p.goles_visitante, eq_v.nombre AS visitante,
                   f.nombre AS fase, p.estado,
                   -- goles de Paraguay en este partido
                   CASE WHEN eq_l.nombre ILIKE '%paraguay%' THEN p.goles_local
                        ELSE p.goles_visitante END AS goles_py
            FROM partido p
            JOIN equipo eq_l ON p.equipo_local_id = eq_l.id
            JOIN equipo eq_v ON p.equipo_visitante_id = eq_v.id
            JOIN fase f ON p.fase_id = f.id
            WHERE eq_l.nombre ILIKE '%paraguay%' OR eq_v.nombre ILIKE '%paraguay%'
            ORDER BY p.numero_fifa
        """))
        rows = r.fetchall()

        total = 0
        print("\n=== PARTIDOS PARAGUAY ===")
        print(f"{'#FIFA':<6} {'Local':<25} {'GL':>3} {'GV':>3} {'Visitante':<25} {'GolPY':>6} {'Fase':<20} Estado")
        print("-" * 100)
        for row in rows:
            pid, num, local, gl, gv, visitante, fase, estado, goles_py = row
            goles_py_v = goles_py if goles_py is not None else 0
            total += goles_py_v
            py_local = '(L)' if 'paraguay' in local.lower() else '   '
            print(f"P{str(num or '?'):<5} {local:<25} {gl or '?':>3} {gv or '?':>3} {visitante:<25} {py_local} {goles_py_v:>3}   {fase:<20} {estado}")

        print(f"\nTOTAL goles Paraguay en BD: {total}")
        print(f"CORRECTO según admin:        3")

        if total == 4:
            print("\n⚠  Hay 1 gol extra de Paraguay. Partido probable: vs Australia (debe ser 0).")
            # Buscar el partido contra Australia
            r2 = await conn.execute(text("""
                SELECT p.id, p.numero_fifa,
                       eq_l.nombre AS local, p.goles_local, p.goles_visitante, eq_v.nombre AS visitante,
                       CASE WHEN eq_l.nombre ILIKE '%paraguay%' THEN 'local' ELSE 'visitante' END AS py_lado
                FROM partido p
                JOIN equipo eq_l ON p.equipo_local_id = eq_l.id
                JOIN equipo eq_v ON p.equipo_visitante_id = eq_v.id
                WHERE (eq_l.nombre ILIKE '%paraguay%' OR eq_v.nombre ILIKE '%paraguay%')
                  AND (eq_l.nombre ILIKE '%australia%' OR eq_v.nombre ILIKE '%australia%')
            """))
            aus_rows = r2.fetchall()
            for aus_row in aus_rows:
                pid2, num2, local2, gl2, gv2, visit2, py_lado = aus_row
                print(f"\nPartido vs Australia: P{num2} | {local2} {gl2}-{gv2} {visit2}")
                print(f"Paraguay es: {py_lado}")
                if py_lado == 'local' and gl2 and gl2 > 0:
                    print(f"  → FIX: UPDATE partido SET goles_local = 0 WHERE id = {pid2};")
                elif py_lado == 'visitante' and gv2 and gv2 > 0:
                    print(f"  → FIX: UPDATE partido SET goles_visitante = 0 WHERE id = {pid2};")
                else:
                    print("  → Goles Paraguay ya son 0 en este partido. Revisar otro partido.")

    await engine.dispose()

asyncio.run(main())
