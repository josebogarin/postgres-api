# -*- coding: utf-8 -*-
"""
clubes_scoring.py — Endpoints aparte del router gigante apostador_bets.py:
  · POST /bets/calcular-puntajes-clubes/{torneo_id}  (reglamento nuevo de clubes)
  · GET  /bets/partido-detalle/{partido_id}          (replay de cualquier partido
        terminado, misma forma que el Live/En Vivo — sirve para el popup
        "recuperar partido").
"""
import json as _json

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import CurrentAdmin, BECBUCSession as DBSession
from app.services.scoring.clubes_calculator import calcular_clubes

router = APIRouter()

_sust_col_partido_ok = False


@router.post("/calcular-puntajes-clubes/{torneo_id}",
             summary="Calcula puntajes de un torneo de clubes (ida/vuelta, reglamento nuevo)")
async def calcular_puntajes_clubes(torneo_id: int, current: CurrentAdmin, db: DBSession) -> dict:
    try:
        return await calcular_clubes(db, torneo_id)
    except Exception as e:
        import traceback
        raise HTTPException(500, f"Error calculando clubes: {e}\n{traceback.format_exc()}")


# Mismo SELECT que /live-panel (para que el popup use el componente del Live tal cual),
# pero filtrando por p.id en vez de numero_fifa. Incluye sustituciones (Cambios).
_PARTIDO_SQL = """
    SELECT
        p.id,
        COALESCE(p.numero_fifa, 0)            AS numero_fifa,
        COALESCE(el.nombre_es, el.nombre)    AS equipo_local,
        COALESCE(ev.nombre_es, ev.nombre)    AS equipo_visitante,
        el.codigo_iso                         AS bandera_local,
        ev.codigo_iso                         AS bandera_visitante,
        p.goles_local, p.goles_visitante,
        p.estado, p.fecha,
        p.minuto_actual, p.minuto_primer_gol,
        COALESCE(p.amarillas, 0)              AS amarillas,
        COALESCE(p.rojas, 0)                  AS rojas,
        COALESCE(p.decisiones_var, 0)         AS decisiones_var,
        p.sustituciones                       AS sustituciones,
        p.penales_partido,
        p.penales_local                       AS penales_tanda_local,
        p.penales_visitante                   AS penales_tanda_visitante,
        p.equipo_clasificado_id,
        f.nombre                              AS fase_nombre,
        f.tipo                                AS fase_tipo,
        el.logo_url                           AS logo_local,
        ev.logo_url                           AS logo_visitante,
        el.api_team_id                        AS local_api_team_id,
        ev.api_team_id                        AS visita_api_team_id,
        p.eventos_api::text                   AS eventos_api_raw,
        (el.nombre ILIKE '%%paraguay%%'
         OR ev.nombre ILIKE '%%paraguay%%')   AS es_paraguay
    FROM partido p
    JOIN fase f ON f.id = p.fase_id
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE p.id = :pid
    LIMIT 1
"""


@router.get("/partido-detalle/{partido_id}",
            summary="Detalle completo de un partido (para el popup de replay del Live)")
async def partido_detalle(partido_id: int, db: DBSession) -> dict:
    """Devuelve un partido con la misma forma que /live-panel (partido), para que el
    popup 'recuperar partido' reutilice el componente del Live. Lectura publica."""
    global _sust_col_partido_ok
    if not _sust_col_partido_ok:
        try:
            await db.execute(text("ALTER TABLE partido ADD COLUMN IF NOT EXISTS sustituciones INT"))
            await db.commit()
        except Exception:
            pass
        _sust_col_partido_ok = True

    r = await db.execute(text(_PARTIDO_SQL), {"pid": partido_id})
    row = r.mappings().fetchone()
    if not row:
        return {"partido": None}
    d = dict(row)
    raw = d.pop("eventos_api_raw", None)
    try:
        d["eventos_api"] = _json.loads(raw) if raw else []
    except Exception:
        d["eventos_api"] = []
    if d.get("fecha") is not None and hasattr(d["fecha"], "strftime"):
        d["fecha"] = d["fecha"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"partido": d}
