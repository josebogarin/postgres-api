"""
ver_mejores_terceros.py
Calcula y muestra el ranking de los 12 mejores terceros según criterio FIFA 2026.
Criterio: Pts → DG → GF → Fair Play (↓menor=mejor) → Ranking FIFA → Grupo
Ejecutar: python ver_mejores_terceros.py
"""
import sys
import os
import asyncio

# ── Path setup ───────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(BASE, "backend")
sys.path.insert(0, BACKEND)

# ── DB directa via asyncpg ────────────────────────────────────────────────────
import asyncpg


DB_DSN = "postgresql://app_user:app_password@localhost:5432/becbuc"

# Intentar leer la DSN del entorno o del config del backend
try:
    from app.core.config import settings
    DB_DSN = settings.DATABASE_URL_BECBUC or settings.DATABASE_URL or DB_DSN
except Exception:
    pass

TORNEO_ID = 2  # Copa del Mundo 2026


async def get_standings(conn):
    """
    Trae standings por grupo desde la vista participacion + partido.
    Equivalente a _calc_standings_reales en apostador_bets.py.
    """
    rows = await conn.fetch("""
        SELECT
            f.nombre              AS fase,
            g.nombre              AS grupo,
            e.nombre              AS nombre,
            e.nombre_es           AS nombre_es,
            e.codigo_iso,
            e.fifa_ranking,
            e.fair_play_pts       AS fp_equipo,
            p2.pj, p2.pg, p2.pe, p2.pp,
            p2.gf, p2.gc,
            p2.gf - p2.gc        AS gd,
            p2.pts,
            -- Sumar amarillas y rojas POR EQUIPO desde los partidos de grupo
            COALESCE((
                SELECT SUM(local_amarillas)
                  FROM partido pa
                  JOIN participacion pa2 ON pa2.equipo_id = e.id
                   AND pa2.torneo_id = :tid
                  JOIN fase ff ON ff.id = pa.fase_id AND ff.torneo_id = :tid
                 WHERE pa.equipo_local_id = e.id
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)
            + COALESCE((
                SELECT SUM(visitante_amarillas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id AND ff.torneo_id = :tid
                 WHERE pa.equipo_visitante_id = e.id
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)  AS amarillas_acum,
            COALESCE((
                SELECT SUM(local_rojas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id AND ff.torneo_id = :tid
                 WHERE pa.equipo_local_id = e.id
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)
            + COALESCE((
                SELECT SUM(visitante_rojas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id AND ff.torneo_id = :tid
                 WHERE pa.equipo_visitante_id = e.id
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)  AS rojas_acum
        FROM participacion p2
        JOIN equipo e ON e.id = p2.equipo_id
        JOIN fase f ON f.id = p2.fase_id
        JOIN (
            SELECT DISTINCT ON (fa.id) fa.id, fa.nombre
              FROM fase fa
             WHERE fa.torneo_id = :tid
               AND fa.tipo ILIKE '%grupo%'
             ORDER BY fa.id
        ) gfase ON gfase.id = p2.fase_id
        LEFT JOIN (
            -- obtener nombre del grupo (sub-tabla distinta por fase si hay sub-grupos)
            SELECT equipo_id, fase_id, nombre AS grupo_nombre
              FROM participacion
             WHERE torneo_id = :tid
        ) gn ON gn.equipo_id = p2.equipo_id AND gn.fase_id = p2.fase_id
        WHERE p2.torneo_id = :tid
        ORDER BY f.nombre, p2.pts DESC, (p2.gf - p2.gc) DESC, p2.gf DESC
    """, tid=TORNEO_ID)
    return rows


async def main():
    print("Conectando a la BD...")
    # Intentar distintas passwords comunes del proyecto
    passwords = ["app_password", "postgres", "becbuc2026", "secret", "password"]
    conn = None
    for pw in passwords:
        try:
            dsn = f"postgresql://app_user:{pw}@localhost:5432/becbuc"
            conn = await asyncpg.connect(dsn, timeout=5)
            print(f"✓ Conectado (password: {pw[:3]}***)")
            break
        except Exception:
            continue

    if conn is None:
        # Intentar leer del .env del backend
        env_file = os.path.join(BACKEND, ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if "BECBUC" in line and "DATABASE" in line and "=" in line:
                        dsn = line.split("=", 1)[1].strip().strip('"').strip("'")
                        try:
                            conn = await asyncpg.connect(dsn, timeout=5)
                            print(f"✓ Conectado via .env")
                            break
                        except Exception:
                            pass
    if conn is None:
        print("✗ No se pudo conectar. Verifica que Docker core-postgres esté activo.")
        print("  Ejecutar: docker ps | findstr postgres")
        sys.exit(1)

    try:
        await run_calc(conn)
    finally:
        await conn.close()


async def run_calc(conn):
    # Traer grupos y equipos
    grupos_raw = await conn.fetch("""
        SELECT
            f.nombre                 AS grupo,
            e.nombre                 AS nombre,
            e.nombre_es,
            e.fifa_ranking,
            p.pts, p.pj, p.pg, p.pe, p.pp,
            p.gf, p.gc,
            (p.gf - p.gc)           AS gd,
            -- Fair play desde columnas por equipo en partido
            COALESCE((
                SELECT SUM(pa.local_amarillas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id
                 WHERE pa.equipo_local_id = e.id
                   AND ff.torneo_id = $1
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)
            + COALESCE((
                SELECT SUM(pa.visitante_amarillas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id
                 WHERE pa.equipo_visitante_id = e.id
                   AND ff.torneo_id = $1
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)                    AS amarillas,
            COALESCE((
                SELECT SUM(pa.local_rojas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id
                 WHERE pa.equipo_local_id = e.id
                   AND ff.torneo_id = $1
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)
            + COALESCE((
                SELECT SUM(pa.visitante_rojas)
                  FROM partido pa
                  JOIN fase ff ON ff.id = pa.fase_id
                 WHERE pa.equipo_visitante_id = e.id
                   AND ff.torneo_id = $1
                   AND ff.tipo ILIKE '%grupo%'
                   AND pa.estado = 'finalizado'
            ), 0)                    AS rojas
        FROM participacion p
        JOIN equipo e ON e.id = p.equipo_id
        JOIN fase f ON f.id = p.fase_id AND f.torneo_id = $1 AND f.tipo ILIKE '%grupo%'
        WHERE p.torneo_id = $1
        ORDER BY f.nombre, p.pts DESC, (p.gf - p.gc) DESC, p.gf DESC
    """, TORNEO_ID)

    if not grupos_raw:
        print("✗ Sin datos de grupos para torneo_id=2. ¿El torneo está inicializado?")
        return

    # Organizar por grupo
    grupos = {}
    for r in grupos_raw:
        g = r["grupo"]
        if g not in grupos:
            grupos[g] = []
        fp = (r["amarillas"] or 0) + (r["rojas"] or 0) * 3
        grupos[g].append({
            "nombre":      r["nombre_es"] or r["nombre"],
            "grupo":       g,
            "pts":         r["pts"],
            "pj":          r["pj"],
            "pg":          r["pg"],
            "pe":          r["pe"],
            "pp":          r["pp"],
            "gf":          r["gf"],
            "gc":          r["gc"],
            "gd":          r["gd"],
            "amarillas":   r["amarillas"],
            "rojas":       r["rojas"],
            "fair_play_pts": fp,
            "fifa_ranking":  r["fifa_ranking"],
        })

    # Extraer el 3° de cada grupo
    terceros = []
    for g_nombre in sorted(grupos.keys()):
        equipos = grupos[g_nombre]
        # Ordenar por criterio FIFA dentro del grupo
        equipos.sort(key=lambda x: (
            -x["pts"], -x["gd"], -x["gf"],
            x["fair_play_pts"],
            x["fifa_ranking"] or 9999,
            x["nombre"],
        ))
        if len(equipos) >= 3:
            tercero = equipos[2].copy()
            tercero["grupo"] = g_nombre
            terceros.append(tercero)

    if not terceros:
        print("✗ No hay suficientes equipos por grupo.")
        return

    # Ranking FIFA: pts → DG → GF → FP↓ → FIFA ranking → grupo
    terceros.sort(key=lambda x: (
        -x["pts"],
        -x["gd"],
        -x["gf"],
        x["fair_play_pts"],
        x["fifa_ranking"] or 9999,
        x["grupo"],
    ))

    # ── Mostrar resultado ────────────────────────────────────────────────────
    SEP = "─" * 95
    HEADER = f"{'#':<4} {'Grupo':<8} {'Equipo':<22} {'PJ':>3} {'PG':>3} {'PE':>3} {'PP':>3} " \
             f"{'GF':>3} {'GC':>3} {'DG':>4} {'Pts':>4} {'Amar':>5} {'Rojas':>5} {'FP↓':>4} {'FIFA':>5}"

    print()
    print("=" * 95)
    print("  RANKING MEJORES 8 TERCEROS — COPA DEL MUNDO 2026 (criterio FIFA)")
    print("  FP = Fair Play = Amarillas×1 + Rojas×3  (menor = mejor)")
    print("=" * 95)
    print(HEADER)
    print(SEP)

    fp_todos_cero = all(t["fair_play_pts"] == 0 for t in terceros)
    if fp_todos_cero:
        print("  ⚠️  AVISO: fair_play_pts = 0 para todos los equipos.")
        print("     Correr primero: POST /api/v1/bets/recalc-fair-play/2")
        print("     (botón 'Recalc. Fair Play' en Herramientas del portal)")
        print(SEP)

    for i, t in enumerate(terceros):
        pos = i + 1
        clasifica = pos <= 8
        marca = "✅ CLASIFICA" if clasifica else "❌"
        if i == 7:
            print(f"{'─'*4}─{'─'*8}─{'─'*22}─{'─'*3}─{'─'*3}─{'─'*3}─{'─'*3}─{'─'*3}─{'─'*3}─{'─'*4}─{'─'*4}─{'─'*5}─{'─'*5}─{'─'*4}─{'─'*5}")
        dg = f"+{t['gd']}" if t['gd'] >= 0 else str(t['gd'])
        fp_str = str(t['fair_play_pts']) if t['fair_play_pts'] else "0"
        fifa_str = str(t['fifa_ranking']) if t['fifa_ranking'] else "—"
        row = (
            f"{pos:<4} {t['grupo']:<8} {t['nombre'][:22]:<22} "
            f"{t['pj']:>3} {t['pg']:>3} {t['pe']:>3} {t['pp']:>3} "
            f"{t['gf']:>3} {t['gc']:>3} {dg:>4} {t['pts']:>4} "
            f"{t['amarillas']:>5} {t['rojas']:>5} {fp_str:>4} {fifa_str:>5}  "
            f"{marca}"
        )
        print(row)

    print(SEP)
    print()
    clasifican = [t["nombre"] for t in terceros[:8]]
    eliminados = [t["nombre"] for t in terceros[8:]]
    print(f"  CLASIFICAN (8): {', '.join(clasifican)}")
    print(f"  ELIMINADOS (4): {', '.join(eliminados)}")
    print()

    # Mostrar resumen por grupo
    print("─" * 95)
    print("  STANDINGS COMPLETOS POR GRUPO (para contexto)")
    print("─" * 95)
    for g_nombre in sorted(grupos.keys()):
        equipos = grupos[g_nombre]
        equipos.sort(key=lambda x: (
            -x["pts"], -x["gd"], -x["gf"],
            x["fair_play_pts"], x["fifa_ranking"] or 9999,
        ))
        print(f"\n  {'━'*60}")
        print(f"  GRUPO {g_nombre}:")
        print(f"  {'Pos':<4} {'Equipo':<22} {'Pts':>4} {'DG':>4} {'GF':>3}  {'FP':>3}")
        for j, e in enumerate(equipos):
            pfx = "  " + ("1°" if j==0 else "2°" if j==1 else "3°" if j==2 else "4°")
            dg  = f"+{e['gd']}" if e['gd'] >= 0 else str(e['gd'])
            fp  = str(e['fair_play_pts'])
            print(f"  {j+1:<4} {e['nombre'][:22]:<22} {e['pts']:>4} {dg:>4} {e['gf']:>3}  {fp:>3}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
