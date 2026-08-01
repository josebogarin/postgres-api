# -*- coding: utf-8 -*-
"""
ranking_repo.py — Acceso a datos del ranking de apostadores (Fase 2).

Encapsula el SQL crudo que antes vivia dentro del endpoint `ranking` de
apostador_bets.py. Cada funcion hace UNA consulta y devuelve estructuras
listas para que el router solo agregue/serialice. Comportamiento identico
al original (mismos SELECT, mismo manejo de errores devolviendo vacio).
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Items de puntaje_detalle que suman al total de partidos
_ITEMS = [
    "pts_resultado", "pts_marcador", "pts_amarillas", "pts_rojas",
    "pts_var", "pts_minuto", "pts_penales_partido", "pts_penales_tanda", "pts_equipo",
]
_SUM_EXPR = " + ".join(f"COALESCE(pd.{c}, 0)" for c in _ITEMS)


async def fetch_puntajes_por_item(db: AsyncSession, torneo_id: int) -> list[dict]:
    """Puntajes totales y por item desde puntaje_detalle (fuente unica)."""
    try:
        rd = await db.execute(
            text(f"""
                SELECT
                    pd.apostador_id,
                    COALESCE(SUM({_SUM_EXPR}), 0)::int AS puntos_partidos_total,
                    COUNT(DISTINCT pd.partido_id)::int  AS apuestas_total,
                    SUM(CASE WHEN COALESCE(pd.pts_marcador,0) > 0 THEN 1 ELSE 0 END)::int AS plenos,
                    SUM(CASE WHEN COALESCE(pd.pts_resultado,0) > 0
                              AND COALESCE(pd.pts_marcador,0) = 0
                             THEN 1 ELSE 0 END)::int AS aciertos,
                    SUM(CASE WHEN COALESCE(pd.pts_resultado,0) = 0
                              AND COALESCE(pd.pts_marcador,0) = 0
                             THEN 1 ELSE 0 END)::int AS fallos,
                    COALESCE(SUM(pd.pts_resultado),                   0)::int AS cat_resultado,
                    COALESCE(SUM(pd.pts_marcador),                    0)::int AS cat_marcador,
                    COALESCE(SUM(pd.pts_amarillas),                   0)::int AS cat_amarillas,
                    COALESCE(SUM(COALESCE(pd.pts_rojas,0)),           0)::int AS cat_rojas,
                    COALESCE(SUM(pd.pts_var),                         0)::int AS cat_var,
                    -- En clubes pts_var almacena las Sustituciones (reemplazan a VAR).
                    COALESCE(SUM(pd.pts_var),                         0)::int AS cat_sustituciones,
                    COALESCE(SUM(pd.pts_minuto),                      0)::int AS cat_minuto,
                    COALESCE(SUM(COALESCE(pd.pts_penales_partido,0)), 0)::int AS cat_penales_partido,
                    COALESCE(SUM(COALESCE(pd.pts_penales_tanda,0)),   0)::int AS cat_penales_tanda,
                    COALESCE(SUM(COALESCE(pd.pts_equipo,0)),          0)::int AS cat_equipo
                FROM puntaje_detalle pd
                WHERE pd.torneo_id = :tid
                GROUP BY pd.apostador_id
            """),
            {"tid": torneo_id},
        )
        return [dict(row) for row in rd.mappings()]
    except Exception:
        await db.rollback()
        return []


async def fetch_globales(db: AsyncSession, torneo_id: int) -> tuple[dict, dict]:
    """Puntajes globales A-G. Devuelve (global_pts, glob_detalle_map)."""
    try:
        rg = await db.execute(
            text("""SELECT apostador_id, pts_total,
                       COALESCE(pts_campeon,0) AS pts_a,
                       COALESCE(pts_finalistas,0) AS pts_b,
                       COALESCE(pts_goleador,0) AS pts_c,
                       COALESCE(pts_peor_equipo,0) AS pts_d,
                       COALESCE(pts_mayor_goleada,0) AS pts_e,
                       COALESCE(pts_etapa_paraguay,0) AS pts_f,
                       COALESCE(pts_goles_paraguay,0) AS pts_g
                FROM puntaje_global WHERE torneo_id = :tid"""),
            {"tid": torneo_id},
        )
        global_pts: dict = {}
        glob_detalle_map: dict = {}
        for row in rg.mappings():
            aid = row["apostador_id"]
            global_pts[aid] = row["pts_total"]
            glob_detalle_map[aid] = {
                "a": int(row["pts_a"] or 0), "b": int(row["pts_b"] or 0),
                "c": int(row["pts_c"] or 0), "d": int(row["pts_d"] or 0),
                "e": int(row["pts_e"] or 0), "f": int(row["pts_f"] or 0),
                "g": int(row["pts_g"] or 0),
            }
        return global_pts, glob_detalle_map
    except Exception:
        return {}, {}


async def fetch_grupos_p(db: AsyncSession, torneo_id: int) -> dict:
    """Puntos P de grupos (apostador_clasificados)."""
    try:
        rc = await db.execute(
            text("""
                SELECT apostador_id, COALESCE(pts_obtenidos, 0) AS pts_grupos_p
                FROM apostador_clasificados
                WHERE torneo_id = :tid AND fase_tipo = 'grupo'
            """),
            {"tid": torneo_id},
        )
        return {row["apostador_id"]: int(row["pts_grupos_p"] or 0) for row in rc.mappings()}
    except Exception:
        return {}


async def fetch_pts_equipo_ko(db: AsyncSession, torneo_id: int) -> dict:
    """pts_equipo por fase KO (desglose P por fase en el arbol)."""
    clasifica_ko_by_uid: dict = {}
    try:
        _sql_ko_p = text(
            "SELECT pd.apostador_id, f.tipo AS fase_tipo, "
            "SUM(COALESCE(pd.pts_equipo,0)) AS pts_p "
            "FROM puntaje_detalle pd "
            "JOIN partido p ON p.id = pd.partido_id "
            "JOIN fase f ON f.id = p.fase_id "
            "WHERE pd.torneo_id = :tid AND NOT (f.tipo ILIKE 'grupo%%') "
            "AND COALESCE(pd.pts_equipo,0) > 0 "
            "GROUP BY pd.apostador_id, f.tipo"
        )
        rp = await db.execute(_sql_ko_p, {"tid": torneo_id})
        for _rp in rp.mappings():
            clasifica_ko_by_uid.setdefault(_rp["apostador_id"], {})[_rp["fase_tipo"]] = int(_rp["pts_p"] or 0)
    except Exception:
        pass
    return clasifica_ko_by_uid


async def fetch_peor_equipo_d(db: AsyncSession, torneo_id: int) -> dict:
    """Puntos D (peor equipo) por separado."""
    try:
        rd2 = await db.execute(
            text("SELECT apostador_id, COALESCE(pts_peor_equipo, 0) AS pts_d FROM puntaje_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        return {row["apostador_id"]: int(row["pts_d"] or 0) for row in rd2.mappings()}
    except Exception:
        return {}


async def fetch_fases_por_uid(db: AsyncSession, torneo_id: int) -> dict:
    """Desglose de puntos por fase, agrupado por apostador."""
    try:
        rf = await db.execute(
            text(f"""
                SELECT
                    pd.apostador_id,
                    f.id AS fase_id,
                    f.tipo AS fase_tipo,
                    f.nombre AS fase_nombre,
                    COALESCE(SUM({_SUM_EXPR}), 0)::int AS pts_fase
                FROM puntaje_detalle pd
                JOIN partido p ON p.id = pd.partido_id
                JOIN fase f ON f.id = p.fase_id
                WHERE pd.torneo_id = :tid
                GROUP BY pd.apostador_id, f.id, f.tipo, f.nombre
                ORDER BY pd.apostador_id, f.id
            """),
            {"tid": torneo_id},
        )
        fases_raw = [dict(row) for row in rf.mappings()]
    except Exception:
        fases_raw = []

    fases_by_uid: dict = {}
    for fr in fases_raw:
        uid = fr["apostador_id"]
        fases_by_uid.setdefault(uid, []).append({
            "tipo": fr["fase_tipo"],
            "nombre": fr["fase_nombre"],
            "pts": fr["pts_fase"],
        })
    return fases_by_uid


async def fetch_apostadores(app_engine, ids: list[int]) -> tuple[dict, dict]:
    """
    Apostadores activos (rol 'apostador') desde app_db + nombres de los ids dados.
    Devuelve (apostadores_all, user_map).
    """
    async with app_engine.connect() as conn:
        ar = await conn.execute(
            text("""
                SELECT u.id, u.username
                FROM users u
                JOIN user_roles ur ON ur.user_id = u.id
                JOIN roles ro ON ro.id = ur.role_id
                WHERE ro.name = 'apostador' AND u.is_active = TRUE
            """)
        )
        apostadores_all = {row["id"]: row["username"] for row in ar.mappings()}
        user_map = dict(apostadores_all)
        if ids:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
            for row in ur.mappings():
                user_map[row["id"]] = row["username"]
    return apostadores_all, user_map
