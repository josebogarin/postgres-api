"""
diag_clasificados.py — Diagnóstico del algoritmo item P (equipos clasificados grupos)
Ejecutar con: python diag_clasificados.py
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import asyncio
import sys
sys.path.insert(0, _osp.path.join(_BASE, 'backend'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

def get_db_url():
    try:
        with open(_osp.path.join(_BASE, 'backend', '.env')) as f:
            for line in f:
                if 'DATABASE_BECBUC_URL' in line:
                    return line.split('=',1)[1].strip().strip('"\'')
    except Exception:
        pass
    return "postgresql+asyncpg://app_user:superpassword@localhost:5432/becbuc"

async def main():
    url = get_db_url()
    print(f"Conectando a: {url[:50]}...")
    engine = create_async_engine(url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:

        # ── 1. Ver tabla apostador_clasificados ───────────────────────────────
        print("\n=== apostador_clasificados (torneo_id=2, fase_tipo='grupo') ===")
        r = await db.execute(text("""
            SELECT ac.apostador_id,
                   ac.aciertos,
                   ac.pts_por_acierto,
                   ac.pts_obtenidos,
                   array_length(ac.equipos_pronosticados, 1) AS pred_count,
                   array_length(ac.equipos_reales, 1)        AS real_count,
                   ac.calculado_at
            FROM apostador_clasificados ac
            WHERE ac.torneo_id = 2 AND ac.fase_tipo = 'grupo'
            ORDER BY ac.pts_obtenidos DESC
        """))
        rows = list(r.mappings())
        if not rows:
            print("  ⚠️  Tabla vacía — calculate_clasificados nunca se corrió o no tiene datos")
        else:
            print(f"  {'apostador_id':>12} {'aciertos':>8} {'pts_ppa':>7} {'pts_obt':>7} {'pred_N':>6} {'real_N':>6}")
            for row in rows:
                print(f"  {row['apostador_id']:>12} {row['aciertos']:>8} {row['pts_por_acierto']:>7} "
                      f"{row['pts_obtenidos']:>7} {row['pred_count'] or '?':>6} {row['real_count'] or '?':>6}")
            print(f"\n  MAX pts_obtenidos = {max(r['pts_obtenidos'] for r in rows)}")
            print(f"  MIN pts_obtenidos = {min(r['pts_obtenidos'] for r in rows)}")
            print(f"  AVG pts_obtenidos = {sum(r['pts_obtenidos'] for r in rows)/len(rows):.1f}")
            print(f"  MAX aciertos = {max(r['aciertos'] for r in rows)}")
            print(f"  MAX pred_count = {max((r['pred_count'] or 0) for r in rows)}")
            print(f"  MAX real_count = {max((r['real_count'] or 0) for r in rows)}")

        # ── 2. Verificar real_r32 ─────────────────────────────────────────────
        print("\n=== Equipos REALES en R32 (ronda32 / 16avos) ===")
        r2 = await db.execute(text("""
            SELECT DISTINCT
                unnest(ARRAY[p.equipo_local_id, p.equipo_visitante_id]) AS equipo_id,
                f.tipo AS fase_tipo, f.nombre AS fase_nombre
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2
              AND (LOWER(f.tipo) = 'ronda32' OR LOWER(f.tipo) LIKE '%ronda32%'
                   OR LOWER(f.tipo) LIKE '%16avos%')
              AND p.equipo_local_id IS NOT NULL
              AND p.equipo_visitante_id IS NOT NULL
              AND p.equipo_local_id > 0
              AND p.equipo_visitante_id > 0
        """))
        real_rows = list(r2.mappings())
        print(f"  Total equipos únicos en real_r32: {len(real_rows)}")
        # Mostrar fases que matchearon
        fases_match = set((r['fase_tipo'], r['fase_nombre']) for r in real_rows)
        for ft, fn in sorted(fases_match):
            print(f"    → fase_tipo='{ft}', nombre='{fn}'")

        # ── 3. Contar partidos en fase ronda32 ────────────────────────────────
        print("\n=== Partidos en ronda32 ===")
        r3 = await db.execute(text("""
            SELECT f.tipo, f.nombre, COUNT(*) as n_partidos,
                   COUNT(DISTINCT p.equipo_local_id) + COUNT(DISTINCT p.equipo_visitante_id) as n_equipos_distintos
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = 2
              AND (LOWER(f.tipo) = 'ronda32' OR LOWER(f.tipo) LIKE '%ronda32%'
                   OR LOWER(f.tipo) LIKE '%16avos%')
            GROUP BY f.tipo, f.nombre
        """))
        for row in r3.mappings():
            print(f"  tipo='{row['tipo']}', nombre='{row['nombre']}' → "
                  f"{row['n_partidos']} partidos, {row['n_equipos_distintos']} equipos distintos")

        # ── 4. Chequeo de pred_teams para apostadores con pts > 32 ───────────
        print("\n=== Apostadores con pts_obtenidos > 32 (imposible teóricamente) ===")
        r4 = await db.execute(text("""
            SELECT ac.apostador_id, ac.pts_obtenidos, ac.aciertos,
                   ac.equipos_pronosticados, ac.equipos_reales
            FROM apostador_clasificados ac
            WHERE ac.torneo_id = 2 AND ac.fase_tipo = 'grupo'
              AND ac.pts_obtenidos > 32
        """))
        high_rows = list(r4.mappings())
        if not high_rows:
            print("  ✅ Ninguno — todos dentro del rango esperado (≤ 32)")
        for row in high_rows:
            pred = row['equipos_pronosticados'] or []
            real = row['equipos_reales'] or []
            inter = set(pred) & set(real)
            print(f"  apostador_id={row['apostador_id']}")
            print(f"    pts_obtenidos={row['pts_obtenidos']}, aciertos={row['aciertos']}")
            print(f"    len(pred)={len(pred)}, len(real)={len(real)}, len(interseccion)={len(inter)}")
            if len(pred) > 32:
                print(f"    ⚠️  PRED TIENE MÁS DE 32 EQUIPOS! ({len(pred)})")
            if len(real) > 32:
                print(f"    ⚠️  REAL TIENE MÁS DE 32 EQUIPOS! ({len(real)})")

        # ── 5. Verificar ranking: pts_grupos_p vs cat_equipo ─────────────────
        print("\n=== Ranking: comparativa pts_grupos_p vs cat_equipo (puntaje_detalle) ===")
        r5 = await db.execute(text("""
            SELECT
                pd.apostador_id,
                COALESCE(ac.pts_obtenidos, 0)          AS pts_grupos_p,
                SUM(COALESCE(pd.pts_equipo, 0))        AS cat_equipo_ko,
                COALESCE(ac.aciertos, 0)               AS aciertos_grupo
            FROM puntaje_detalle pd
            JOIN partido p ON p.id = pd.partido_id
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN apostador_clasificados ac
                ON ac.apostador_id = pd.apostador_id
               AND ac.torneo_id = 2
               AND ac.fase_tipo = 'grupo'
            WHERE pd.torneo_id = 2
            GROUP BY pd.apostador_id, ac.pts_obtenidos, ac.aciertos
            HAVING COALESCE(ac.pts_obtenidos, 0) > 0
            ORDER BY pts_grupos_p DESC
            LIMIT 15
        """))
        print(f"  {'apostador_id':>12} {'pts_grupos_p':>12} {'aciertos_g':>10} {'cat_equipo_KO':>13}")
        for row in r5.mappings():
            flag = " ⚠️  > 32" if int(row['pts_grupos_p']) > 32 else ""
            print(f"  {row['apostador_id']:>12} {row['pts_grupos_p']:>12} {row['aciertos_grupo']:>10} "
                  f"{int(row['cat_equipo_ko'] or 0):>13}{flag}")

    await engine.dispose()
    print("\n✅ Diagnóstico completado.")

asyncio.run(main())
