"""
preview_ranking_postfix.py — Muestra el ranking corregido ANTES de aplicar el SQL fix.
Simula el resultado como si ya se hubiera ejecutado fix_pts_equipo_grupos.sql.
Ejecutar con: python preview_ranking_postfix.py
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

def get_app_url():
    try:
        with open(r'C:\proyecto FAST API\backend\.env') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    return line.split('=',1)[1].strip().strip('"\'')
    except Exception: pass
    return "postgresql+asyncpg://app_user:superpassword@localhost:5432/app_db"

async def main():
    engine_b = create_async_engine(get_db_url(), echo=False)
    engine_a = create_async_engine(get_app_url(), echo=False)
    Session_b = sessionmaker(engine_b, class_=AsyncSession, expire_on_commit=False)
    Session_a = sessionmaker(engine_a, class_=AsyncSession, expire_on_commit=False)

    async with Session_a() as dba:
        # Aliases de apostadores
        r = await dba.execute(text(
            "SELECT id, username AS alias FROM users WHERE id IN "
            "(SELECT user_id FROM user_roles ur JOIN roles r ON r.id=ur.role_id WHERE r.name='apostador')"
        ))
        alias_map = {row["id"]: row["alias"] for row in r.mappings()}

    async with Session_b() as db:

        # 1. pts_partidos corregido (sin pts_equipo de grupos)
        r1 = await db.execute(text("""
            SELECT pd.apostador_id,
                   SUM(
                     COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0)
                   + COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0)
                   + COALESCE(pd.pts_var,0)       + COALESCE(pd.pts_minuto,0)
                   + COALESCE(pd.pts_penales_partido,0) + COALESCE(pd.pts_penales_tanda,0)
                   -- pts_equipo: SOLO si la fase NO es grupo
                   + CASE WHEN LOWER(f.tipo) NOT LIKE '%grupo%'
                          THEN COALESCE(pd.pts_equipo,0) ELSE 0 END
                   )::int AS pts_partidos_correcto,
                   -- para referencia: cuánto era el error
                   SUM(CASE WHEN LOWER(f.tipo) LIKE '%grupo%'
                            THEN COALESCE(pd.pts_equipo,0) ELSE 0 END)::int AS pts_equipo_grupo_erroneo
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE pd.torneo_id = 2
            GROUP BY pd.apostador_id
        """))
        pts_partidos = {r["apostador_id"]: (int(r["pts_partidos_correcto"]), int(r["pts_equipo_grupo_erroneo"]))
                        for r in r1.mappings()}

        # 2. pts_globales
        r2 = await db.execute(text(
            "SELECT apostador_id, COALESCE(pts_total,0) AS pts_glob "
            "FROM puntaje_global WHERE torneo_id=2"
        ))
        pts_glob = {r["apostador_id"]: int(r["pts_glob"]) for r in r2.mappings()}

        # 3. pts_grupos_p (apostador_clasificados)
        r3 = await db.execute(text(
            "SELECT apostador_id, COALESCE(pts_obtenidos,0) AS pts_p "
            "FROM apostador_clasificados WHERE torneo_id=2 AND fase_tipo='grupo'"
        ))
        pts_gp = {r["apostador_id"]: int(r["pts_p"]) for r in r3.mappings()}

        # Todos los apostadores con puntajes
        all_ids = set(pts_partidos) | set(pts_glob) | set(pts_gp)

        rows = []
        for uid in all_ids:
            if uid not in alias_map:
                continue
            pp, error = pts_partidos.get(uid, (0,0))
            pg = pts_glob.get(uid, 0)
            gp = pts_gp.get(uid, 0)
            total = pp + pg + gp
            rows.append({
                "uid": uid,
                "alias": alias_map[uid],
                "pts_partidos": pp,
                "pts_glob": pg,
                "pts_grupos_p": gp,
                "total": total,
                "error_quitado": error,
            })

        rows.sort(key=lambda x: -x["total"])

        print(f"\n{'Pos':>3} {'Apostador':20} {'Partidos':>8} {'GlobAG':>6} {'P-Grp':>5} {'TOTAL':>6} {'Error-quitado':>14}")
        print("-" * 75)
        for i, r in enumerate(rows, 1):
            marker = " ←" if r["alias"].lower() in ("checho","seba","hs","lav","vitra") else ""
            print(f"{i:>3} {r['alias']:20} {r['pts_partidos']:>8} {r['pts_glob']:>6} "
                  f"{r['pts_grupos_p']:>5} {r['total']:>6} {r['error_quitado']:>14}{marker}")

        print(f"\nTotal apostadores: {len(rows)}")
        print("\n(Error-quitado = pts_equipo que se le restará a pts_partidos al ejecutar el SQL fix)")

    await engine_b.dispose()
    await engine_a.dispose()

asyncio.run(main())
