"""
diag_p_clasificados.py — Diagnóstico completo del ítem P.
Verifica:
  1. Real R32: 32 equipos que clasificaron realmente
  2. Por apostador: equipos predichos vs reales (aciertos, pts_grupos_p)
  3. R32 KO (pts_equipo en puntaje_detalle): suma y max con Paraguay
Ejecutar: python diag_p_clasificados.py
"""
import asyncio, sys
sys.path.insert(0, r'C:\proyecto FAST API\backend')
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

def get_becbuc_url():
    try:
        with open(r'C:\proyecto FAST API\backend\.env') as f:
            for line in f:
                if 'DATABASE_BECBUC_URL' in line:
                    return line.split('=',1)[1].strip().strip('"\'')
    except: pass
    return "postgresql+asyncpg://app_user:superpassword@localhost:5432/becbuc"

def get_app_url():
    try:
        with open(r'C:\proyecto FAST API\backend\.env') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    return line.split('=',1)[1].strip().strip('"\'')
    except: pass
    return "postgresql+asyncpg://app_user:superpassword@localhost:5432/app_db"

TORNEO_ID = 2

async def main():
    eng_b = create_async_engine(get_becbuc_url(), echo=False)
    eng_a = create_async_engine(get_app_url(), echo=False)
    Sb = sessionmaker(eng_b, class_=AsyncSession, expire_on_commit=False)
    Sa = sessionmaker(eng_a, class_=AsyncSession, expire_on_commit=False)

    async with Sa() as dba:
        r = await dba.execute(text(
            "SELECT id, username FROM users u "
            "JOIN user_roles ur ON ur.user_id=u.id "
            "JOIN roles ro ON ro.id=ur.role_id "
            "WHERE ro.name='apostador'"
        ))
        alias_map = {row["id"]: row["username"] for row in r.mappings()}

    async with Sb() as db:

        # ── 1. Real R32: 32 equipos ──────────────────────────────────────────
        r = await db.execute(text("""
            SELECT DISTINCT unnest(ARRAY[p.equipo_local_id, p.equipo_visitante_id]) AS eid,
                   e.nombre
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            JOIN equipo e ON e.id = ANY(ARRAY[p.equipo_local_id, p.equipo_visitante_id])
            WHERE f.torneo_id=:tid AND LOWER(f.tipo) LIKE '%ronda32%'
              AND p.equipo_local_id IS NOT NULL AND p.equipo_visitante_id IS NOT NULL
        """), {"tid": TORNEO_ID})
        real_r32 = {row["eid"]: row["nombre"] for row in r.mappings()}
        print(f"\n=== REAL R32: {len(real_r32)} equipos ===")
        for eid, nm in sorted(real_r32.items(), key=lambda x: x[1]):
            print(f"  {eid:4d}  {nm}")

        # ── 2. Paraguay en R32 ───────────────────────────────────────────────
        r = await db.execute(text("""
            SELECT p.id, p.numero_fifa,
                   el.nombre AS local, ev.nombre AS visitante,
                   p.equipo_local_id, p.equipo_visitante_id,
                   p.goles_local, p.goles_visitante,
                   p.equipo_clasificado_id,
                   epar.nombre AS ganador
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            LEFT JOIN equipo epar ON epar.id = p.equipo_clasificado_id
            WHERE f.torneo_id=:tid AND LOWER(f.tipo) LIKE '%ronda32%'
              AND (el.nombre ILIKE '%paraguay%' OR ev.nombre ILIKE '%paraguay%')
        """), {"tid": TORNEO_ID})
        rows_par = list(r.mappings())
        if rows_par:
            p = rows_par[0]
            print(f"\n=== PARAGUAY en R32: P{p['numero_fifa']} {p['local']} {p['goles_local']}-{p['goles_visitante']} {p['visitante']} → CLASIFICADO: {p['ganador']} ===")
            print(f"  Doble puntaje: SI → max pts_equipo este partido = 4 (2×2 Paraguay mult)")
        
        # ── 3. pts_equipo R32 por apostador ─────────────────────────────────
        r = await db.execute(text("""
            SELECT pd.apostador_id, SUM(pd.pts_equipo) AS ko_p,
                   COUNT(*) AS partidos_con_pts
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            WHERE pd.torneo_id=:tid AND LOWER(f.tipo) LIKE '%ronda32%'
              AND COALESCE(pd.pts_equipo,0)>0
            GROUP BY pd.apostador_id
            ORDER BY ko_p DESC
        """), {"tid": TORNEO_ID})
        ko_p_rows = list(r.mappings())
        print(f"\n=== KO P (ronda32 pts_equipo) — Max sin Paraguay=32, con Paraguay=34 ===")
        print(f"{'Apostador':20} {'pts_equipo':>10} {'#partidos':>10}")
        for row in ko_p_rows[:10]:
            alias = alias_map.get(row["apostador_id"], f"uid={row['apostador_id']}")
            print(f"  {alias:20} {int(row['ko_p']):>10} {int(row['partidos_con_pts']):>10}")

        # ── 4. pts_grupos_p (apostador_clasificados) ─────────────────────────
        r = await db.execute(text("""
            SELECT ac.apostador_id, ac.aciertos, ac.pts_obtenidos,
                   array_length(ac.equipos_pronosticados, 1) AS pred_count,
                   array_length(ac.equipos_reales, 1) AS real_count
            FROM apostador_clasificados ac
            WHERE ac.torneo_id=:tid AND ac.fase_tipo='grupo'
            ORDER BY ac.pts_obtenidos DESC
        """), {"tid": TORNEO_ID})
        gp_rows = list(r.mappings())
        print(f"\n=== GRUPOS P (apostador_clasificados) — Max=32 ===")
        print(f"{'Apostador':20} {'pred_count':>10} {'real_count':>10} {'aciertos':>9} {'pts':>5}")
        for row in gp_rows[:10]:
            alias = alias_map.get(row["apostador_id"], f"uid={row['apostador_id']}")
            pred_c = row["pred_count"] or 0
            real_c = row["real_count"] or 0
            print(f"  {alias:20} {pred_c:>10} {real_c:>10} {int(row['aciertos']):>9} {int(row['pts_obtenidos']):>5}")
        
        # Verificar si algún apostador tiene pred_count != 32
        anomalias = [r for r in gp_rows if (r["pred_count"] or 0) != 32 or (r["aciertos"] or 0) > 32]
        if anomalias:
            print(f"\n⚠️  ANOMALÍAS: {len(anomalias)} apostadores con pred_count≠32 o aciertos>32:")
            for row in anomalias:
                alias = alias_map.get(row["apostador_id"], f"uid={row['apostador_id']}")
                print(f"  {alias}: pred={row['pred_count']}, aciertos={row['aciertos']}, pts={row['pts_obtenidos']}")
        else:
            print(f"\n✅ Todos los apostadores con pred_count=32 y aciertos<=32")
        
        print(f"\nTotal apostadores en apostador_clasificados (grupo): {len(gp_rows)}")

    await eng_b.dispose()
    await eng_a.dispose()

asyncio.run(main())
