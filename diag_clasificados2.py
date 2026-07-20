"""
diag_clasificados2.py — Diagnóstico pts_equipo por fase en puntaje_detalle
Ejecutar con: python diag_clasificados2.py
"""
import asyncio, sys
sys.path.insert(0, r'C:\proyecto FAST API\backend')
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

def get_db_url():
    try:
        with open(r'C:\proyecto FAST API\backend\.env') as f:
            for line in f:
                if 'DATABASE_BECBUC_URL' in line:
                    return line.split('=',1)[1].strip().strip('"\'')
    except Exception: pass
    return "postgresql+asyncpg://app_user:superpassword@localhost:5432/becbuc"

async def main():
    engine = create_async_engine(get_db_url(), echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:

        # ── 1. pts_equipo por fase en puntaje_detalle ─────────────────────────
        print("\n=== pts_equipo TOTAL por fase (todos los apostadores) ===")
        r = await db.execute(text("""
            SELECT f.tipo, f.nombre,
                   COUNT(DISTINCT pd.apostador_id) AS n_apos,
                   COUNT(DISTINCT pd.partido_id)   AS n_partidos,
                   SUM(COALESCE(pd.pts_equipo,0))  AS total_pts_equipo,
                   MAX(pd.pts_equipo)               AS max_partido
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE pd.torneo_id = 2
              AND COALESCE(pd.pts_equipo,0) > 0
            GROUP BY f.tipo, f.nombre
            ORDER BY f.tipo
        """))
        rows = list(r.mappings())
        if not rows:
            print("  ✅ pts_equipo = 0 en todas las fases (sin P scoring en puntaje_detalle)")
        else:
            print(f"  {'fase_tipo':20} {'n_apos':>6} {'n_partidos':>10} {'total_pts':>9} {'max_por_partido':>15}")
            for row in rows:
                print(f"  {row['tipo']:20} {row['n_apos']:>6} {row['n_partidos']:>10} "
                      f"{int(row['total_pts_equipo'] or 0):>9} {int(row['max_partido'] or 0):>15}")

        # ── 2. Verificar si partidos de grupo tienen equipo_clasificado_id ────
        print("\n=== Partidos de grupo con equipo_clasificado_id NOT NULL ===")
        r2 = await db.execute(text("""
            SELECT COUNT(*) AS n_con_clasificado,
                   COUNT(CASE WHEN equipo_clasificado_id IS NULL THEN 1 END) AS n_sin_clasificado
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2 AND LOWER(f.tipo) LIKE '%grupo%'
        """))
        row = dict(r2.mappings().one())
        print(f"  Con equipo_clasificado_id: {row['n_con_clasificado']}")
        print(f"  Sin equipo_clasificado_id: {row['n_sin_clasificado']}")

        # ── 3. Para UN apostador (el de mayor pts_grupos_p): desglose completo
        print("\n=== Desglose pts_equipo por fase para el apostador con más pts ===")
        r3 = await db.execute(text("""
            SELECT ac.apostador_id, ac.pts_obtenidos
            FROM apostador_clasificados ac
            WHERE ac.torneo_id = 2 AND ac.fase_tipo = 'grupo'
            ORDER BY ac.pts_obtenidos DESC LIMIT 1
        """))
        top = dict(r3.mappings().one())
        uid = top['apostador_id']
        print(f"  apostador_id={uid}, pts_grupos_p={top['pts_obtenidos']}")

        r4 = await db.execute(text("""
            SELECT f.tipo, f.nombre,
                   COUNT(DISTINCT pd.partido_id)  AS n_partidos,
                   SUM(COALESCE(pd.pts_equipo,0)) AS pts_equipo_fase
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE pd.torneo_id = 2 AND pd.apostador_id = :uid
            GROUP BY f.tipo, f.nombre
            ORDER BY pts_equipo_fase DESC
        """), {"uid": uid})
        total_pe = 0
        for row in r4.mappings():
            pe = int(row['pts_equipo_fase'] or 0)
            total_pe += pe
            if pe > 0:
                flag = "  ← GRUPO (¿doble conteo?)" if 'grupo' in str(row['tipo']).lower() else ""
                print(f"    {row['tipo']:20} | partidos={row['n_partidos']:3} | pts_equipo={pe}{flag}")
        print(f"    TOTAL pts_equipo (cat_equipo en ranking): {total_pe}")
        print(f"    pts_grupos_p (apostador_clasificados):    {top['pts_obtenidos']}")
        print(f"    SUMA COMBINADA que muestra ranking:       {total_pe + top['pts_obtenidos']}")
        if total_pe > 32:
            print(f"    ⚠️  pts_equipo total > 32 — posible doble conteo o error en puntaje_detalle")

        # ── 4. cat_equipo en ranking endpoint (query real) ───────────────────
        print("\n=== cat_equipo calculado por ranking endpoint (SUM sin filtro de fase) ===")
        r5 = await db.execute(text("""
            SELECT pd.apostador_id,
                   SUM(COALESCE(pd.pts_equipo,0)) AS cat_equipo_total,
                   SUM(CASE WHEN LOWER(f.tipo) LIKE '%grupo%'
                            THEN COALESCE(pd.pts_equipo,0) ELSE 0 END) AS cat_equipo_grupos,
                   SUM(CASE WHEN LOWER(f.tipo) NOT LIKE '%grupo%'
                            THEN COALESCE(pd.pts_equipo,0) ELSE 0 END) AS cat_equipo_ko
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE pd.torneo_id = 2
              AND COALESCE(pd.pts_equipo,0) > 0
            GROUP BY pd.apostador_id
            ORDER BY cat_equipo_total DESC
            LIMIT 10
        """))
        print(f"  {'apos_id':>8} {'total':>6} {'grupos':>7} {'KO':>5}  {'doble?':>7}")
        for row in r5.mappings():
            dbl = " ⚠️" if int(row['cat_equipo_grupos'] or 0) > 0 else ""
            print(f"  {row['apostador_id']:>8} {int(row['cat_equipo_total'] or 0):>6} "
                  f"{int(row['cat_equipo_grupos'] or 0):>7} {int(row['cat_equipo_ko'] or 0):>5}{dbl}")

    await engine.dispose()
    print("\n✅ Diagnóstico 2 completado.")

asyncio.run(main())
