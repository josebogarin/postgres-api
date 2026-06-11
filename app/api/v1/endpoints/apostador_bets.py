"""
Endpoints del módulo de apuestas para apostadores.

GET   /bets/partidos/{torneo_id}        → partidos pendientes de grupo
GET   /bets/mis-apuestas/{torneo_id}    → apuestas del usuario autenticado
POST  /bets/apuestas                    → crear o actualizar una apuesta
GET   /bets/periodo/{torneo_id}         → período de apuestas configurado
PATCH /bets/periodo/{torneo_id}         → configurar período (solo admin)
GET   /bets/grupos/{torneo_id}          → standings de grupos para simulación
GET   /bets/mi-bracket/{torneo_id}      → bracket personal simulado
GET   /bets/ranking/{torneo_id}         → ranking de puntos del torneo
GET   /bets/auditoria/{torneo_id}       → lista de snapshots de auditoría
POST  /bets/auditoria/{torneo_id}       → generar Excel de auditoría (admin)
GET   /bets/auditoria/download/{id}     → descargar snapshot
GET   /bets/mensajes/{torneo_id}        → mensajes del admin visibles para todos
POST  /bets/mensajes/{torneo_id}        → crear mensaje (solo admin)
DELETE /bets/mensajes/{torneo_id}/{id}  → eliminar mensaje (solo admin)
"""

import json
import logging
import os
import random
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, BECBUCSession as DBSession
from app.db.session import engine as _app_engine

from app.services.bracket_service import (
    simular_standings_usuario,
    seleccionar_mejores_terceros,
    armar_ronda32,
    propagar_ko_usuario,
)
from app.services import ko_scoring
from app.services.ko_scoring import PHASE_MULT, TIPO_NUM_RANGE, KO_FEEDERS  # noqa: F401
from app.services.scoring import registry as scoring_registry
from app.services.scoring.calculator import ScoringCalculator

router = APIRouter()


# ── Schemas ─────────────────────────────────────────────────────────────────

class ApuestaIn(BaseModel):
    partido_id:      int
    pred_local:      int
    pred_visitante:  int
    pred_minuto_gol: int | None = None   # 1-90, None = no predicó
    pred_amarillas:  int | None = None   # 0+,   None = no predicó
    pred_var:        int | None = None   # 0+,   None = no predicó
    pred_penales:    bool | None = None  # legacy bool (no borrar)
    pred_rojas:                   int | None = None  # K: tarjetas rojas
    pred_penales_partido:         int | None = None  # M: penales sancionados en partido
    pred_penales_local_tanda:     int | None = None  # O: goles local en tanda
    pred_penales_visitante_tanda: int | None = None  # O: goles visitante en tanda


class PeriodoIn(BaseModel):
    apuesta_inicio: datetime | None = None
    apuesta_fin:    datetime | None = None


class MensajeIn(BaseModel):
    titulo:    str
    contenido: str


# ── Helper: período de apuestas ──────────────────────────────────────────────

async def _get_periodo(db: DBSession, torneo_id: int) -> dict:
    """Devuelve {apuesta_inicio, apuesta_fin, abierto} para el torneo."""
    try:
        r = await db.execute(
            text("SELECT apuesta_inicio, apuesta_fin FROM torneo WHERE id = :tid"),
            {"tid": torneo_id}
        )
        row = r.one_or_none()
    except Exception:
        # Columnas no migradas aún → período abierto por defecto
        return {"apuesta_inicio": None, "apuesta_fin": None, "abierto": True}

    if not row:
        raise HTTPException(404, "Torneo no encontrado")

    inicio, fin = row[0], row[1]
    now = datetime.now(timezone.utc)
    abierto = True
    if inicio and now < inicio:
        abierto = False
    if fin and now > fin:
        abierto = False
    return {
        "apuesta_inicio": inicio.isoformat() if inicio else None,
        "apuesta_fin":    fin.isoformat()    if fin    else None,
        "abierto":        abierto,
    }


async def _check_admin(current: CurrentUser) -> bool:
    async with _app_engine.connect() as conn:
        ur = await conn.execute(
            text("""
                SELECT r.name FROM users u
                JOIN user_roles ur2 ON ur2.user_id = u.id
                JOIN roles r ON r.id = ur2.role_id
                WHERE u.id = :uid AND r.name IN ('admin','superadmin')
                LIMIT 1
            """),
            {"uid": current.id}
        )
        return ur.one_or_none() is not None


async def _check_superadmin(current: CurrentUser) -> bool:
    async with _app_engine.connect() as conn:
        ur = await conn.execute(
            text("""
                SELECT r.name FROM users u
                JOIN user_roles ur2 ON ur2.user_id = u.id
                JOIN roles r ON r.id = ur2.role_id
                WHERE u.id = :uid AND r.name = 'superadmin'
                LIMIT 1
            """),
            {"uid": current.id}
        )
        return ur.one_or_none() is not None


_audit_logger = logging.getLogger("becbuc.audit")


async def _audit_log(action: str, resource: str, *, current=None,
                     details: dict | None = None, status_code: int = 200,
                     method: str = "EVENT", path: str = "", resource_id: str | None = None):
    """Escribe un registro explícito en audit_logs (app_db) con detalle JSON.

    Usado para eventos de dominio (simulación, avance de fase, reset, intentos de
    modificar fases encerradas). No interrumpe el flujo si falla el registro.
    """
    uid = getattr(current, "id", None)
    uemail = getattr(current, "email", None) or getattr(current, "username", None)
    try:
        async with _app_engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO audit_logs
                        (user_id, user_email, action, resource, resource_id,
                         method, path, status_code, ip_address, details)
                    VALUES
                        (:uid, :uemail, :action, :resource, :rid,
                         :method, :path, :status, NULL, CAST(:details AS json))
                """),
                {"uid": uid, "uemail": uemail, "action": action, "resource": resource,
                 "rid": resource_id, "method": method, "path": path,
                 "status": status_code,
                 "details": json.dumps(details or {}, ensure_ascii=False, default=str)},
            )
    except Exception:
        _audit_logger.exception("No se pudo escribir audit_log: %s/%s", resource, action)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/partidos/{torneo_id}", summary="Partidos de grupo pendientes de jugar")
async def partidos_pendientes(torneo_id: int, db: DBSession) -> list[dict]:
    r = await db.execute(
        text("""
            SELECT
                p.id, p.fase_id, p.jornada, p.fecha, p.estado,
                f.nombre  AS fase_nombre,
                el.id     AS local_id,
                el.nombre AS local_nombre,
                el.nombre_es AS local_nombre_es,
                el.logo_url  AS local_logo,
                ev.id     AS visit_id,
                ev.nombre AS visit_nombre,
                ev.nombre_es AS visit_nombre_es,
                ev.logo_url  AS visit_logo
            FROM partido p
            JOIN fase  f  ON f.id  = p.fase_id  AND f.tipo = 'grupo'
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid
              AND p.estado IN ('programado', 'aplazado')
            ORDER BY f.nombre, p.jornada, p.fecha NULLS LAST
        """),
        {"tid": torneo_id}
    )
    return [dict(row) for row in r.mappings()]


@router.get("/mis-apuestas/{torneo_id}", summary="Apuestas del usuario en el torneo")
async def mis_apuestas(
    torneo_id: int,
    current: CurrentUser,
    db: DBSession,
    for_apostador_id: int = None,
) -> list[dict]:
    # Admin puede ver apuestas de otro apostador
    target_id = current.id
    if for_apostador_id and await _check_admin(current):
        target_id = for_apostador_id
    r = await db.execute(
        text("""
            SELECT
                a.id, a.partido_id, a.pred_local, a.pred_visitante,
                a.pred_ganador, a.puntos,
                COALESCE(a.pred_minuto_gol, NULL) AS pred_minuto_gol,
                COALESCE(a.pred_amarillas,  NULL) AS pred_amarillas,
                COALESCE(a.pred_var,        NULL) AS pred_var,
                a.pred_penales,
                COALESCE(a.pred_rojas,                   NULL) AS pred_rojas,
                COALESCE(a.pred_penales_local_tanda,     NULL) AS pred_penales_local_tanda,
                COALESCE(a.pred_penales_visitante_tanda, NULL) AS pred_penales_visitante_tanda,
                COALESCE(a.pred_penales_partido,          NULL) AS pred_penales_partido,
                COALESCE(a.puntos_bonus,    0)    AS puntos_bonus,
                a.updated_at,
                p.goles_local, p.goles_visitante, p.estado AS partido_estado,
                COALESCE(p.minuto_primer_gol, NULL) AS minuto_primer_gol,
                COALESCE(p.amarillas,         NULL) AS amarillas,
                COALESCE(p.decisiones_var,    NULL) AS decisiones_var,
                el.nombre AS local_nombre, el.nombre_es AS local_nombre_es,
                ev.nombre AS visit_nombre, ev.nombre_es AS visit_nombre_es,
                f.nombre  AS fase_nombre
            FROM apuesta a
            JOIN partido p  ON p.id  = a.partido_id
            JOIN fase    f  ON f.id  = p.fase_id
            JOIN equipo el  ON el.id = p.equipo_local_id
            JOIN equipo ev  ON ev.id = p.equipo_visitante_id
            WHERE a.apostador_id = :uid
              AND p.torneo_id    = :tid
            ORDER BY f.nombre, p.jornada, p.fecha NULLS LAST
        """),
        {"uid": target_id, "tid": torneo_id}
    )
    return [dict(row) for row in r.mappings()]


@router.get("/periodo/{torneo_id}", summary="Período de apuestas del torneo")
async def get_periodo(torneo_id: int, db: DBSession) -> dict:
    return await _get_periodo(db, torneo_id)


@router.patch("/periodo/{torneo_id}", summary="Configurar período de apuestas (admin)")
async def set_periodo(torneo_id: int, body: PeriodoIn, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    await db.execute(
        text("UPDATE torneo SET apuesta_inicio=:ini, apuesta_fin=:fin WHERE id=:tid"),
        {"ini": body.apuesta_inicio, "fin": body.apuesta_fin, "tid": torneo_id}
    )
    await db.commit()
    return await _get_periodo(db, torneo_id)


@router.post("/apuestas", summary="Crear o actualizar apuesta")
async def upsert_apuesta(body: ApuestaIn, current: CurrentUser, db: DBSession) -> dict:
    # Verificar partido
    r = await db.execute(
        text("SELECT estado, torneo_id FROM partido WHERE id = :pid"),
        {"pid": body.partido_id}
    )
    row = r.one_or_none()
    if not row:
        raise HTTPException(404, "Partido no encontrado")
    if row[0] == "finalizado":
        raise HTTPException(400, "El partido ya finalizó, no se pueden modificar apuestas")

    # Verificar período de apuestas
    periodo = await _get_periodo(db, row[1])
    if not periodo["abierto"]:
        fin = periodo.get("apuesta_fin")
        msg = (f"El período de apuestas cerró el {fin}"
               if fin else "El período de apuestas aún no ha comenzado")
        raise HTTPException(400, msg)

    await db.execute(
        text("""
            INSERT INTO apuesta
                (apostador_id, partido_id, pred_local, pred_visitante,
                 pred_minuto_gol, pred_amarillas, pred_var, pred_penales,
                 pred_rojas, pred_penales_partido, pred_penales_local_tanda, pred_penales_visitante_tanda)
            VALUES
                (:uid, :pid, :pl, :pv, :pmg, :pam, :pvar, :ppen,
                 :projas, :ppp, :pltanda, :pvtanda)
            ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                pred_local                   = EXCLUDED.pred_local,
                pred_visitante               = EXCLUDED.pred_visitante,
                pred_minuto_gol              = EXCLUDED.pred_minuto_gol,
                pred_amarillas               = EXCLUDED.pred_amarillas,
                pred_var                     = EXCLUDED.pred_var,
                pred_penales                 = EXCLUDED.pred_penales,
                pred_rojas                   = EXCLUDED.pred_rojas,
                pred_penales_partido         = EXCLUDED.pred_penales_partido,
                pred_penales_local_tanda     = EXCLUDED.pred_penales_local_tanda,
                pred_penales_visitante_tanda = EXCLUDED.pred_penales_visitante_tanda,
                updated_at                   = NOW()
        """),
        {
            "uid":    current.id,
            "pid":    body.partido_id,
            "pl":     body.pred_local,
            "pv":     body.pred_visitante,
            "pmg":    body.pred_minuto_gol,
            "pam":    body.pred_amarillas,
            "pvar":   body.pred_var,
            "ppen":   body.pred_penales,
            "projas": body.pred_rojas,
            "ppp":    body.pred_penales_partido,
            "pltanda": body.pred_penales_local_tanda,
            "pvtanda": body.pred_penales_visitante_tanda,
        }
    )
    await db.commit()
    return {"ok": True, "partido_id": body.partido_id,
            "pred": f"{body.pred_local} - {body.pred_visitante}"}


@router.post("/resetear-apuestas/{torneo_id}",
             summary="Resetear (anular) todas las apuestas del usuario para el torneo (sin restricciones de estado/periodo)")
async def resetear_apuestas(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """Reset completo del usuario para el torneo: pone en NULL todos los campos de
    predicción (incluyendo bonus y tanda), borra puntaje_detalle, apuesta_global y
    puntaje_global. No verifica estado de partido ni período de apuestas.
    """
    uid = current.id
    tid = torneo_id
    partido_ids_subq = """
        SELECT p.id FROM partido p
        JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = :tid
    """

    # 1. NULL todas las predicciones de apuesta (campos base + bonus + tanda)
    r = await db.execute(
        text(f"""
            UPDATE apuesta SET
                pred_local                   = NULL,
                pred_visitante               = NULL,
                pred_penales                 = NULL,
                pred_minuto_gol              = NULL,
                pred_amarillas               = NULL,
                pred_var                     = NULL,
                pred_rojas                   = NULL,
                pred_penales_partido         = NULL,
                pred_penales_local_tanda     = NULL,
                pred_penales_visitante_tanda = NULL,
                puntos                       = 0,
                puntos_bonus                 = 0,
                updated_at                   = NOW()
            WHERE apostador_id = :uid
              AND partido_id IN ({partido_ids_subq})
        """),
        {"uid": uid, "tid": tid},
    )

    # 2. Borrar puntaje_detalle del usuario (afecta ranking y transparencia)
    await db.execute(
        text(f"""
            DELETE FROM puntaje_detalle
            WHERE apostador_id = :uid
              AND partido_id IN ({partido_ids_subq})
        """),
        {"uid": uid, "tid": tid},
    )

    # 3. Borrar pronósticos globales A-G del usuario
    await db.execute(
        text("DELETE FROM apuesta_global WHERE apostador_id = :uid AND torneo_id = :tid"),
        {"uid": uid, "tid": tid},
    )

    # 4. Borrar puntaje global calculado del usuario
    await db.execute(
        text("DELETE FROM puntaje_global WHERE apostador_id = :uid AND torneo_id = :tid"),
        {"uid": uid, "tid": tid},
    )

    await db.commit()
    return {"ok": True, "actualizadas": r.rowcount}


@router.get("/grupos/{torneo_id}", summary="Standings de grupos para simulación")
async def grupos_standings(torneo_id: int, db: DBSession) -> list[dict]:
    from math import comb

    # Refrescar el cuadro (PJ/Pts/posición) desde los resultados reales en cada carga
    try:
        await _recalc_participacion(db, torneo_id)
        await db.commit()
    except Exception:
        await db.rollback()

    rf = await db.execute(
        text("SELECT id, nombre FROM fase WHERE torneo_id=:tid AND tipo='grupo' ORDER BY nombre"),
        {"tid": torneo_id}
    )
    fases = [dict(r) for r in rf.mappings()]

    result = []
    for fase in fases:
        fid = fase["id"]

        rs = await db.execute(
            text("""
                SELECT e.id AS equipo_id,
                       COALESCE(e.nombre_es, e.nombre) AS nombre,
                       e.logo_url,
                       e.fifa_ranking,
                       pa.pj, pa.pg, pa.pe, pa.pp, pa.gf, pa.gc,
                       (pa.gf - pa.gc) AS gd,
                       pa.pts, pa.clasifica, pa.posicion,
                       COALESCE(pa.fair_play_pts, 0)       AS fair_play_pts,
                       COALESCE(pa.amarillas, 0)            AS amarillas,
                       COALESCE(pa.rojas_directas, 0)       AS rojas_directas,
                       COALESCE(pa.rojas_doble_amarilla, 0) AS rojas_doble_amarilla
                FROM participacion pa
                JOIN equipo e ON e.id = pa.equipo_id
                WHERE pa.fase_id = :fid
                ORDER BY pa.pts DESC, (pa.gf - pa.gc) DESC, pa.gf DESC
            """),
            {"fid": fid}
        )
        standings = [dict(r) for r in rs.mappings()]

        rp = await db.execute(
            text("""
                SELECT
                    p.id, p.estado, p.jornada, p.fecha,
                    p.equipo_local_id     AS local_id,
                    p.equipo_visitante_id AS visit_id,
                    p.goles_local, p.goles_visitante,
                    COALESCE(p.amarillas, NULL)          AS amarillas,
                    COALESCE(p.decisiones_var, NULL)     AS decisiones_var,
                    COALESCE(p.minuto_primer_gol, NULL)  AS minuto_primer_gol,
                    COALESCE(p.rojas, NULL)              AS rojas,
                    p.minuto_actual,
                    el.nombre    AS local_nombre,
                    el.nombre_es AS local_nombre_es,
                    el.logo_url  AS local_logo,
                    ev.nombre    AS visit_nombre,
                    ev.nombre_es AS visit_nombre_es,
                    ev.logo_url  AS visit_logo
                FROM partido p
                JOIN equipo el ON el.id = p.equipo_local_id
                JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE p.fase_id = :fid
                ORDER BY p.jornada, p.fecha NULLS LAST
            """),
            {"fid": fid}
        )
        partidos = [dict(r) for r in rp.mappings()]

        n_equipos = len(standings)
        esperados = comb(n_equipos, 2) if n_equipos >= 2 else 0
        partidos_faltantes = max(0, esperados - len(partidos))

        result.append({
            "fase_id":            fid,
            "fase_nombre":        fase["nombre"],
            "standings":          standings,
            "partidos":           partidos,
            "partidos_esperados": esperados,
            "partidos_faltantes": partidos_faltantes,
        })
    return result


@router.get("/bracket-real/{torneo_id}", summary="Bracket real (resultados oficiales) por número FIFA")
async def bracket_real(torneo_id: int, db: DBSession) -> dict:
    """Devuelve los partidos KO reales mapeados por número FIFA (74..104),
    con equipos reales (ya avanzados por _avanzar_bracket), marcador, penales,
    estado y ganador. Sin auth: lectura pública para el dashboard."""
    maps = await ko_scoring.build_num_maps(db, torneo_id)
    pid2num = maps.get("pid2num", {})
    num2tipo = maps.get("num2tipo", {})
    if not pid2num:
        return {"partidos": []}

    rp = await db.execute(
        text("""
            SELECT p.id, p.estado,
                   p.equipo_local_id     AS local_id,
                   p.equipo_visitante_id AS visit_id,
                   p.goles_local, p.goles_visitante,
                   p.penales_local, p.penales_visitante,
                   el.nombre AS local_nombre, el.nombre_es AS local_nombre_es, el.logo_url AS local_logo,
                   ev.nombre AS visit_nombre, ev.nombre_es AS visit_nombre_es, ev.logo_url AS visit_logo
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid AND f.tipo <> 'grupo'
        """),
        {"tid": torneo_id},
    )

    out = []
    for r in rp.mappings():
        num = pid2num.get(r["id"])
        if not num:
            continue
        gl, gv = r["goles_local"], r["goles_visitante"]
        pl, pv = r["penales_local"], r["penales_visitante"]
        fin = r["estado"] == "finalizado"
        ganador = None
        if fin and gl is not None and gv is not None:
            if gl > gv:
                ganador = "local"
            elif gv > gl:
                ganador = "visitante"
            elif pl is not None and pv is not None and pl != pv:
                ganador = "local" if pl > pv else "visitante"
        out.append({
            "num":        num,
            "tipo":       num2tipo.get(num),
            "finalizado": fin,
            "ganador":    ganador,
            "gl": gl, "gv": gv, "pen_l": pl, "pen_v": pv,
            "local": ({"id": r["local_id"],
                       "nombre": r["local_nombre_es"] or r["local_nombre"],
                       "logo_url": r["local_logo"]} if r["local_id"] else None),
            "visitante": ({"id": r["visit_id"],
                           "nombre": r["visit_nombre_es"] or r["visit_nombre"],
                           "logo_url": r["visit_logo"]} if r["visit_id"] else None),
        })
    return {"partidos": out}


@router.get("/mi-bracket/{torneo_id}", summary="Bracket personal simulado del apostador (R32 → Final)")
async def mi_bracket(
    torneo_id: int,
    current: CurrentUser,
    db: DBSession,
    for_apostador_id: int = None,
) -> dict:
    # Admin puede ver bracket de otro apostador
    target_id = current.id
    if for_apostador_id and await _check_admin(current):
        target_id = for_apostador_id
    standings = await simular_standings_usuario(db, target_id, torneo_id)
    if not standings:
        raise HTTPException(404, "No se encontraron grupos para este torneo")
    mejores, eliminados = seleccionar_mejores_terceros(standings)
    r32_bracket = armar_ronda32(standings, mejores)

    # Propagación completa KO (R32 → Final) usando predicciones del apostador.
    # Mismo algoritmo que el bracket real (ko_scoring); ganadores se derivan de
    # pred_local vs pred_visitante; empate/sin predicción → FIFA ranking.
    try:
        ko_bracket = await propagar_ko_usuario(db, target_id, torneo_id, r32_bracket)
    except Exception:
        # Fallback: build minimal bracket from partido_ids only (sin equipos ni predicciones).
        # Esto ocurre si pred_penales aún no fue migrada u otro error en propagación.
        # El frontend puede igual mostrar los inputs de carga (solo falta el nombre del equipo).
        try:
            from app.services.ko_scoring import build_num_maps as _build_num_maps
            maps = await _build_num_maps(db, torneo_id)
            ko_bracket = []
            for num, pid in maps["num2pid"].items():
                tipo = maps["num2tipo"].get(num, "")
                ko_bracket.append({
                    "num": num, "tipo": tipo, "partido_id": pid,
                    "local_id": None, "visit_id": None,
                    "local": None, "visitante": None,
                    "pred_gl": None, "pred_gv": None, "pred_penales": None,
                    "winner_id": None, "loser_id": None,
                })
        except Exception:
            ko_bracket = []

    return {
        "grupos_simulados": list(standings.values()),
        "mejores_terceros": mejores,
        "terceros_eliminados": eliminados,
        "ronda_32": r32_bracket,
        "ko_bracket": ko_bracket,   # Lista ordenada R32→Final con equipos propagados
    }


@router.get("/stats/{torneo_id}", summary="Estadísticas generales del torneo (para KPIs extra)")
async def stats_torneo(torneo_id: int, db: DBSession) -> dict:
    """Devuelve stats que requieren cruce de DBs: total apostadores, líder, último."""
    total_apostadores = 0
    lider_nombre = "—"
    ultimo_nombre = "—"
    lider_pts = 0
    ultimo_pts = 0

    # Total apostadores registrados (app_db)
    async with _app_engine.connect() as conn:
        r = await conn.execute(text("""
            SELECT COUNT(*) FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles ro ON ro.id = ur.role_id
            WHERE ro.name = 'apostador' AND u.is_active = TRUE
        """))
        total_apostadores = r.scalar() or 0

    # Ranking para líder y último (becbuc)
    try:
        rq = await db.execute(
            text("""
                SELECT a.apostador_id,
                    COALESCE(SUM(a.puntos), 0) AS total
                FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                WHERE p.torneo_id = :tid
                GROUP BY a.apostador_id
                ORDER BY total DESC
            """),
            {"tid": torneo_id}
        )
        ranking_rows = [(row[0], row[1]) for row in rq]
    except Exception:
        await db.rollback()
        try:
            rq = await db.execute(
                text("""
                    SELECT a.apostador_id, COALESCE(SUM(a.puntos), 0) AS total
                    FROM apuesta a
                    JOIN partido p ON p.id = a.partido_id
                    WHERE p.torneo_id = :tid
                    GROUP BY a.apostador_id ORDER BY total DESC
                """),
                {"tid": torneo_id}
            )
            ranking_rows = [(row[0], row[1]) for row in rq]
        except Exception:
            ranking_rows = []

    if ranking_rows:
        lider_id,  lider_pts  = ranking_rows[0]
        ultimo_id, ultimo_pts = ranking_rows[-1]
        ids = list({lider_id, ultimo_id})
        async with _app_engine.connect() as conn:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"),
                {"ids": ids}
            )
            user_map = {row[0]: row[1] for row in ur}
        lider_nombre  = user_map.get(lider_id,  f"#{lider_id}")
        ultimo_nombre = user_map.get(ultimo_id, f"#{ultimo_id}")

    return {
        "total_apostadores": total_apostadores,
        "lider_nombre":      lider_nombre,
        "lider_pts":         int(lider_pts),
        "ultimo_nombre":     ultimo_nombre,
        "ultimo_pts":        int(ultimo_pts),
    }


@router.get("/apostadores", summary="Lista de usuarios con rol apostador (público)")
async def listar_apostadores() -> list[dict]:
    """Devuelve todos los usuarios activos con rol 'apostador'."""
    async with _app_engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT u.id, u.username
                FROM users u
                JOIN user_roles ur ON ur.user_id = u.id
                JOIN roles ro ON ro.id = ur.role_id
                WHERE ro.name = 'apostador'
                  AND u.is_active = TRUE
                ORDER BY u.username
            """)
        )
        return [{"id": row[0], "username": row[1]} for row in r]


@router.get("/mis-partidos/{torneo_id}", summary="Partidos del torneo con puntajes por categoría del apostador")
async def mis_partidos(torneo_id: int, current: CurrentUser, db: DBSession) -> list[dict]:
    """
    Retorna cada partido del torneo con:
    - Datos del partido (estado, minuto_actual, equipos, goles reales, predicciones)
    - Puntaje por categoría (H-P) desde puntaje_detalle
    - Subtotal por partido
    """
    def _sql_partidos(minuto_col: str) -> str:
        return f"""
            SELECT
                p.id                                        AS partido_id,
                p.jornada,
                p.fecha,
                p.estado,
                p.goles_local,
                p.goles_visitante,
                p.amarillas,
                p.rojas,
                p.decisiones_var,
                p.minuto_primer_gol,
                p.penales_local,
                p.penales_visitante,
                COALESCE(p.penales_partido, 0)              AS penales_partido,
                {minuto_col}                                AS minuto_actual,
                f.nombre                                    AS fase_nombre,
                f.tipo                                      AS fase_tipo,
                f.orden                                     AS fase_orden,
                el.id                                       AS local_id,
                COALESCE(el.nombre_es, el.nombre)           AS local_nombre,
                el.logo_url                                 AS local_logo,
                ev.id                                       AS visit_id,
                COALESCE(ev.nombre_es, ev.nombre)           AS visit_nombre,
                ev.logo_url                                 AS visit_logo,
                a.pred_local,
                a.pred_visitante,
                a.pred_minuto_gol,
                a.pred_amarillas,
                a.pred_var,
                a.pred_rojas,
                a.pred_penales,
                a.pred_penales_partido,
                a.pred_penales_local_tanda,
                a.pred_penales_visitante_tanda,
                COALESCE(a.puntos, 0)                       AS puntos_base,
                COALESCE(a.puntos_bonus, 0)                 AS puntos_bonus,
                pd.pts_resultado,
                pd.pts_marcador,
                pd.pts_amarillas,
                pd.pts_var,
                pd.pts_minuto,
                pd.pts_rojas,
                pd.pts_penales_partido,
                pd.pts_penales_tanda,
                COALESCE(pd.pts_equipo, 0)                  AS pts_equipo,
                pd.pts_bonus,
                pd.pts_total
            FROM partido p
            JOIN fase    f  ON f.id  = p.fase_id
            JOIN equipo  el ON el.id = p.equipo_local_id
            JOIN equipo  ev ON ev.id = p.equipo_visitante_id
            LEFT JOIN apuesta a ON a.partido_id = p.id AND a.apostador_id = :uid
            LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = :uid
            WHERE p.torneo_id = :tid
            ORDER BY f.orden, p.jornada NULLS LAST, p.fecha NULLS LAST, p.id
        """
    _qparams = {"uid": current.id, "tid": torneo_id}
    try:
        r = await db.execute(text(_sql_partidos("p.minuto_actual")), _qparams)
    except Exception as _e:
        if "minuto_actual" in str(_e):
            await db.rollback()
            r = await db.execute(text(_sql_partidos("NULL::smallint")), _qparams)
        else:
            raise
    rows = [dict(row) for row in r.mappings()]
    # Calcular subtotal partido = resultado + marcador + bonus (si puntaje_detalle no disponible)
    for row in rows:
        if row.get("pts_total") is None:
            row["pts_total"] = (row.get("puntos_base") or 0) + (row.get("puntos_bonus") or 0)
        # minuto_display
        estado = row.get("estado") or ""
        minuto = row.get("minuto_actual")
        if estado == "finalizado":
            row["minuto_display"] = "Concluido"
        elif estado == "programado":
            row["minuto_display"] = "No iniciado"
        elif minuto is not None:
            row["minuto_display"] = str(int(minuto))
        else:
            row["minuto_display"] = estado.capitalize() if estado else "—"
    return rows


@router.get("/ranking/{torneo_id}", summary="Ranking de apostadores en el torneo con desglose por categoría")
async def ranking(torneo_id: int, db: DBSession) -> list[dict]:
    _sql_base = """
        SELECT
            a.apostador_id,
            COALESCE(SUM(a.puntos),       0)::int AS puntos_partidos,
            COALESCE(SUM(a.puntos_bonus),  0)::int AS puntos_bonus_partido,
            (COALESCE(SUM(a.puntos),0)
             + COALESCE(SUM(a.puntos_bonus),0))::int AS puntos_partidos_total,
            COUNT(a.id)::int                       AS apuestas_total,
            SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3=0  THEN 1 ELSE 0 END)::int AS plenos,
            SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3<>0 THEN 1 ELSE 0 END)::int AS aciertos,
            SUM(CASE WHEN p.estado='finalizado' AND a.puntos=0  THEN 1 ELSE 0 END)::int AS fallos,
            SUM(CASE WHEN p.estado='finalizado'
                     AND COALESCE(a.puntos_bonus,0)>0 THEN 1 ELSE 0 END)::int          AS bonus_count
        FROM apuesta a
        JOIN partido p ON p.id = a.partido_id
        WHERE p.torneo_id = :tid
        GROUP BY a.apostador_id
    """
    try:
        r = await db.execute(text(_sql_base), {"tid": torneo_id})
    except Exception:
        await db.rollback()
        r = await db.execute(text(_sql_base), {"tid": torneo_id})

    rows = [dict(row) for row in r.mappings()]

    # Puntajes globales A-G
    try:
        rg = await db.execute(
            text("SELECT apostador_id, pts_total FROM puntaje_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        global_pts = {row["apostador_id"]: row["pts_total"] for row in rg.mappings()}
    except Exception:
        global_pts = {}

    # Desglose por categoría desde puntaje_detalle
    try:
        rd = await db.execute(
            text("""
                SELECT
                    apostador_id,
                    COALESCE(SUM(pts_resultado),        0)::int AS cat_resultado,
                    COALESCE(SUM(pts_marcador),         0)::int AS cat_marcador,
                    COALESCE(SUM(pts_amarillas),        0)::int AS cat_amarillas,
                    COALESCE(SUM(pts_rojas),            0)::int AS cat_rojas,
                    COALESCE(SUM(pts_var),              0)::int AS cat_var,
                    COALESCE(SUM(pts_minuto),           0)::int AS cat_minuto,
                    COALESCE(SUM(pts_penales_partido),  0)::int AS cat_penales_partido,
                    COALESCE(SUM(pts_penales_tanda),    0)::int AS cat_penales_tanda,
                    COALESCE(SUM(pts_equipo),           0)::int AS cat_equipo
                FROM puntaje_detalle
                WHERE torneo_id = :tid
                GROUP BY apostador_id
            """),
            {"tid": torneo_id},
        )
        cat_pts = {row["apostador_id"]: dict(row) for row in rd.mappings()}
    except Exception:
        cat_pts = {}

    # Todos los apostadores activos (rol 'apostador'), aunque no tengan apuestas
    ids = [row["apostador_id"] for row in rows]
    async with _app_engine.connect() as conn:
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
                {"ids": ids}
            )
            for row in ur.mappings():
                user_map[row["id"]] = row["username"]

    _ZERO_CATS = {
        "cat_resultado": 0, "cat_marcador": 0, "cat_amarillas": 0,
        "cat_rojas": 0, "cat_var": 0, "cat_minuto": 0,
        "cat_penales_partido": 0, "cat_penales_tanda": 0, "cat_equipo": 0,
    }

    present = {row["apostador_id"] for row in rows}
    for uid in apostadores_all:
        if uid not in present:
            rows.append({
                "apostador_id": uid,
                "puntos_partidos": 0, "puntos_bonus_partido": 0,
                "puntos_partidos_total": 0, "apuestas_total": 0,
                "plenos": 0, "aciertos": 0, "fallos": 0, "bonus_count": 0,
            })

    for row in rows:
        uid = row["apostador_id"]
        row["nombre"]          = user_map.get(uid, f"Usuario {uid}")
        pts_globales           = global_pts.get(uid, 0) or 0
        pts_partidos           = row.get("puntos_partidos_total") or 0
        row["pts_globales"]    = pts_globales
        row["puntos_total"]    = pts_partidos + pts_globales
        row.setdefault("puntos_partidos", row.get("puntos_partidos", 0))
        # Merge per-category breakdown
        cats = cat_pts.get(uid, _ZERO_CATS)
        row.update({k: cats.get(k, 0) for k in _ZERO_CATS})

    rows.sort(key=lambda r: (-(r.get("puntos_total") or 0),
                             -(r.get("apuestas_total") or 0),
                             (r.get("nombre") or "").lower()))
    return rows


# ── Simulación y puntajes ────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Helper: resetear puntajes de TODOS los apostadores de un torneo
# Borra puntaje_detalle y puntaje_global; pone puntos/puntos_bonus = 0 en apuesta.
# ─────────────────────────────────────────────────────────────────────────────
async def _reset_puntajes_todos(db: AsyncSession, torneo_id: int) -> dict:
    """
    Vuelve a cero TODOS los puntajes calculados del torneo:
      - apuesta.puntos = 0, puntos_bonus = 0  (para todos los partidos del torneo)
      - DELETE puntaje_detalle WHERE torneo_id
      - DELETE puntaje_global  WHERE torneo_id
    Retorna {"apuestas_zeroed": N, "detalle_borradas": N, "global_borradas": N}
    """
    # 1. Cero en apuesta.puntos / puntos_bonus
    r_a = await db.execute(
        text("""
            UPDATE apuesta
            SET puntos = 0, puntos_bonus = 0
            WHERE partido_id IN (
                SELECT id FROM partido WHERE torneo_id = :tid
            )
        """),
        {"tid": torneo_id},
    )
    apuestas_zeroed = r_a.rowcount or 0

    # 2. Borrar puntaje_detalle (incluye bonus calculados)
    detalle_borradas = 0
    try:
        r_d = await db.execute(
            text("DELETE FROM puntaje_detalle WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        detalle_borradas = r_d.rowcount or 0
    except Exception as _e:
        log.warning("reset_puntajes.detalle_skip", error=str(_e))
        # NO rollback — no cancelar el UPDATE apuesta que ya corrió

    # 3. Borrar puntaje_global (A-G)
    global_borradas = 0
    try:
        r_g = await db.execute(
            text("DELETE FROM puntaje_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        global_borradas = r_g.rowcount or 0
    except Exception as _e:
        log.warning("reset_puntajes.global_skip", error=str(_e))
        # NO rollback

    return {
        "apuestas_zeroed":  apuestas_zeroed,
        "detalle_borradas": detalle_borradas,
        "global_borradas":  global_borradas,
    }


@router.post("/reset-puntajes/{torneo_id}",
             summary="Resetear TODOS los puntajes calculados del torneo (admin)")
async def reset_puntajes(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Vuelve a cero los puntajes de TODOS los apostadores del torneo.
    No borra los pronósticos (apuesta.pred_*) — solo los puntos calculados.
    Útil para recalcular desde cero cuando se modifican reglas de scoring.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    summary = await _reset_puntajes_todos(db, torneo_id)
    await db.commit()
    await _audit_log("reset:puntajes", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/reset-puntajes/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={**summary, "evento": "reset puntajes todos los apostadores"})
    return {"ok": True, "torneo_id": torneo_id, **summary}


@router.post("/reset-grupos-admin/{torneo_id}",
             summary="Reset completo de grupos para TODOS los apostadores (admin)")
async def reset_grupos_admin(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Resetea pronósticos Y puntajes de TODOS los apostadores del torneo:
      - apuesta.pred_* = NULL, puntos = 0, puntos_bonus = 0
      - puntaje_detalle: DELETE
      - puntaje_global: DELETE
      - apuesta_global: DELETE (pronósticos A-G)
    Equivalente al resetear-apuestas pero aplicado a todos los apostadores.
    Usar desde el panel admin cuando se quiere reiniciar la fase de grupos.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    partido_ids_subq = "SELECT id FROM partido WHERE torneo_id = :tid"

    # 1. NULL todos los pronósticos de todos los apostadores del torneo
    r_pred = await db.execute(
        text(f"""
            UPDATE apuesta SET
                pred_local                   = NULL,
                pred_visitante               = NULL,
                pred_penales                 = NULL,
                pred_minuto_gol              = NULL,
                pred_amarillas               = NULL,
                pred_var                     = NULL,
                pred_rojas                   = NULL,
                pred_penales_partido         = NULL,
                pred_penales_local_tanda     = NULL,
                pred_penales_visitante_tanda = NULL,
                puntos                       = 0,
                puntos_bonus                 = 0,
                updated_at                   = NOW()
            WHERE partido_id IN ({partido_ids_subq})
        """),
        {"tid": torneo_id},
    )
    apuestas = r_pred.rowcount or 0

    # 2. Puntaje detalle y global
    pts = await _reset_puntajes_todos(db, torneo_id)

    # 3. Pronósticos globales A-G
    r_ag = await db.execute(
        text("DELETE FROM apuesta_global WHERE torneo_id = :tid"),
        {"tid": torneo_id},
    )
    globales = r_ag.rowcount or 0

    await db.commit()
    await _audit_log("reset:grupos_admin", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/reset-grupos-admin/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={"apuestas": apuestas, "globales": globales, **pts})
    return {
        "ok": True,
        "torneo_id": torneo_id,
        "apuestas_reseteadas": apuestas,
        "globales_borrados": globales,
        **pts,
    }


@router.post("/simular-resultados/{torneo_id}", summary="Simular resultados aleatorios de grupos (admin, solo pruebas)")
async def simular_resultados(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    r = await db.execute(
        text("""
            SELECT p.id FROM partido p
            JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
            WHERE p.torneo_id = :tid
        """),
        {"tid": torneo_id},
    )
    partido_ids = [row[0] for row in r]
    if not partido_ids:
        raise HTTPException(404, "No hay partidos de grupo para este torneo")

    # Resetear puntajes calculados antes de simular (resultado cambia → scores quedan stale)
    await _reset_puntajes_todos(db, torneo_id)

    # Bloqueo: si el torneo ya avanzó a fases KO con resultados, la fase de grupos
    # está encerrada y no se puede re-simular (corrompería el bracket).
    rko = await db.execute(
        text("""SELECT COUNT(*)::int FROM partido p JOIN fase f ON f.id=p.fase_id
                WHERE p.torneo_id=:tid AND f.tipo<>'grupo' AND p.estado='finalizado'"""),
        {"tid": torneo_id})
    ko_finalizados = rko.scalar() or 0
    if ko_finalizados > 0:
        await _audit_log("simulacion:bloqueada", "bets", current=current,
                         status_code=409, method="POST",
                         path=f"/api/v1/bets/simular-resultados/{torneo_id}",
                         resource_id=str(torneo_id),
                         details={"motivo": "fase de grupos encerrada",
                                  "ko_finalizados": ko_finalizados})
        raise HTTPException(409, "La fase de grupos está encerrada: ya hay resultados en fases posteriores. Usá 'Reset total' (superadmin) para reiniciar.")

    for pid in partido_ids:
        gl = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
        gv = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
        # Bonus por partido (solo si la simulación los debe poblar para pruebas)
        minuto = random.randint(1, 90) if (gl + gv) > 0 else None
        amarillas = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 12, 22, 26, 18, 11, 6])[0]
        var = random.choices([0, 1], weights=[65, 35])[0]
        await db.execute(
            text("""
                UPDATE partido
                SET goles_local=:gl, goles_visitante=:gv,
                    minuto_primer_gol=:minuto, amarillas=:amar, rojas=:rojas, decisiones_var=:var,
                    penales_partido=:pen_part, estado='finalizado'
                WHERE id=:pid
            """),
            {"gl": gl, "gv": gv, "minuto": minuto, "amar": amarillas, "rojas": random.choices([0,1,2], weights=[78,18,4])[0], "var": var, "pen_part": random.choices([0,1,2], weights=[70,22,8])[0], "pid": pid},
        )

    await _recalc_participacion(db, torneo_id)
    # Avanzar bracket: R32 toma sus equipos desde los standings de grupos
    maps = await ko_scoring.build_num_maps(db, torneo_id)
    await _avanzar_bracket(db, torneo_id, maps)
    await db.commit()
    await _audit_log("simulacion:grupos", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/simular-resultados/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={"evento": "simular resultados de grupos",
                              "partidos_actualizados": len(partido_ids),
                              "avance_bracket": "R32 desde standings"})
    return {"ok": True, "partidos_actualizados": len(partido_ids)}


@router.post("/simular-fase/{fase_id}", summary="Simular resultados aleatorios de una fase (admin, solo pruebas)")
async def simular_fase(fase_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    rf = await db.execute(
        text("SELECT id, nombre, tipo, torneo_id, COALESCE(bloqueada, FALSE) AS bloqueada FROM fase WHERE id = :fid"),
        {"fid": fase_id},
    )
    fase = rf.mappings().first()
    if not fase:
        raise HTTPException(404, "Fase no encontrada")
    es_grupo = fase["tipo"] == "grupo"

    # Bloqueo: respetar el bloqueo manual del admin
    if fase.get("bloqueada"):
        await _audit_log("simulacion:bloqueada", "bets", current=current,
                         status_code=409, method="POST",
                         path=f"/api/v1/bets/simular-fase/{fase_id}",
                         resource_id=str(fase_id),
                         details={"motivo": "fase bloqueada manualmente", "fase": fase["nombre"]})
        raise HTTPException(409, f"La fase '{fase['nombre']}' está bloqueada. Desbloquéala en Configuración → Fases para simular.")

    r = await db.execute(
        text("SELECT id FROM partido WHERE fase_id = :fid"),
        {"fid": fase_id},
    )
    partido_ids = [row[0] for row in r]
    if not partido_ids:
        raise HTTPException(404, "La fase no tiene partidos")

    for pid in partido_ids:
        gl = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
        gv = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
        minuto = random.randint(1, 90) if (gl + gv) > 0 else None
        amarillas = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 12, 22, 26, 18, 11, 6])[0]
        var = random.choices([0, 1], weights=[65, 35])[0]
        # En eliminatorias no puede haber empate: definir por penales
        pen_l = pen_v = None
        if not es_grupo and gl == gv:
            pen_l, pen_v = random.choice([(4, 2), (5, 4), (3, 1), (5, 3), (4, 5), (2, 4), (1, 3)])
        await db.execute(
            text("""
                UPDATE partido
                SET goles_local=:gl, goles_visitante=:gv,
                    minuto_primer_gol=:minuto, amarillas=:amar, decisiones_var=:var,
                    rojas=:rojas, penales_partido=:pen_part, penales_local=:pl, penales_visitante=:pv,
                    estado='finalizado'
                WHERE id=:pid
            """),
            {"gl": gl, "gv": gv, "minuto": minuto, "amar": amarillas, "rojas": random.choices([0,1,2], weights=[78,18,4])[0], "var": var,
             "pen_part": random.choices([0,1,2], weights=[70,22,8])[0], "pl": pen_l, "pv": pen_v, "pid": pid},
        )

    if es_grupo:
        await _recalc_participacion(db, fase["torneo_id"])
    # Avanzar bracket: propaga ganadores a la(s) fase(s) KO siguiente(s)
    maps = await ko_scoring.build_num_maps(db, fase["torneo_id"])
    await _avanzar_bracket(db, fase["torneo_id"], maps)
    await db.commit()
    await _audit_log("simulacion:fase", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/simular-fase/{fase_id}",
                     resource_id=str(fase_id),
                     details={"evento": "simular fase", "fase": fase["nombre"],
                              "tipo": fase["tipo"],
                              "partidos_actualizados": len(partido_ids),
                              "avance_bracket": True})
    return {"ok": True, "fase": fase["nombre"], "partidos_actualizados": len(partido_ids)}


@router.post("/reset-fase/{fase_id}", summary="Reiniciar resultados de una fase a 'programado' (admin, solo pruebas)")
async def reset_fase(fase_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    rf = await db.execute(
        text("SELECT id, nombre, tipo, torneo_id, COALESCE(bloqueada, FALSE) AS bloqueada FROM fase WHERE id = :fid"),
        {"fid": fase_id},
    )
    fase = rf.mappings().first()
    if not fase:
        raise HTTPException(404, "Fase no encontrada")

    # Bloqueo: respetar el bloqueo manual del admin
    if fase.get("bloqueada"):
        await _audit_log("reset-fase:bloqueada", "bets", current=current,
                         status_code=409, method="POST",
                         path=f"/api/v1/bets/reset-fase/{fase_id}",
                         resource_id=str(fase_id),
                         details={"motivo": "fase bloqueada manualmente", "fase": fase["nombre"]})
        raise HTTPException(409, f"La fase '{fase['nombre']}' está bloqueada. Desbloquéala en Configuración → Fases para reiniciar.")

    r = await db.execute(
        text("SELECT id FROM partido WHERE fase_id = :fid"),
        {"fid": fase_id},
    )
    partido_ids = [row[0] for row in r]
    if not partido_ids:
        raise HTTPException(404, "La fase no tiene partidos")

    # Reiniciar partidos: estado programado + limpiar resultados y bonus
    await db.execute(
        text("""
            UPDATE partido
            SET goles_local=NULL, goles_visitante=NULL,
                minuto_primer_gol=NULL, amarillas=NULL, rojas=NULL, decisiones_var=NULL,
                penales_partido=NULL, penales_local=NULL, penales_visitante=NULL,
                goles_local_prorroga=NULL, goles_visitante_prorroga=NULL,
                estado='programado'
            WHERE fase_id=:fid
        """),
        {"fid": fase_id},
    )
    # Limpiar puntajes de apuestas de esos partidos (las predicciones se conservan)
    await db.execute(
        text("UPDATE apuesta SET puntos=0, puntos_bonus=0 WHERE partido_id = ANY(:pids)"),
        {"pids": partido_ids},
    )

    if fase["tipo"] == "grupo":
        await _recalc_participacion(db, fase["torneo_id"])
    await db.commit()
    await _audit_log("reset:fase", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/reset-fase/{fase_id}",
                     resource_id=str(fase_id),
                     details={"evento": "reiniciar fase", "fase": fase["nombre"],
                              "partidos_reiniciados": len(partido_ids)})
    return {"ok": True, "fase": fase["nombre"], "partidos_reiniciados": len(partido_ids)}


@router.post("/reset-torneo/{torneo_id}", summary="Reset total: borra resultados y pronósticos del torneo (superadmin)")
async def reset_torneo(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_superadmin(current):
        raise HTTPException(403, "Solo el superadmin puede reiniciar el torneo")

    part_subq = "SELECT id FROM partido WHERE torneo_id=:tid"

    # 1) Borrar todas las apuestas (predicciones) del torneo
    #    IMPORTANTE: usar subquery — ANY(:list) no funciona en asyncpg con listas Python
    rd = await db.execute(
        text(f"DELETE FROM apuesta WHERE partido_id IN ({part_subq})"),
        {"tid": torneo_id},
    )
    apuestas_borradas = rd.rowcount or 0

    # 2) Resetear scores de todos los partidos a NULL/programado
    await db.execute(
        text("""
            UPDATE partido
            SET goles_local          = NULL,
                goles_visitante      = NULL,
                minuto_primer_gol    = NULL,
                amarillas            = NULL,
                decisiones_var       = NULL,
                penales_local        = NULL,
                penales_visitante    = NULL,
                estado               = 'programado'
            WHERE torneo_id = :tid
        """),
        {"tid": torneo_id},
    )
    # Columnas opcionales: verificar cuáles existen ANTES de actualizar
    # (evita que una columna faltante ponga la transacción en estado ABORTED)
    _opt_cols_check = await db.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='partido' AND table_schema='public'
          AND column_name = ANY(ARRAY['rojas','penales_partido','equipo_clasificado_id',
                                       'goles_local_prorroga','goles_visitante_prorroga',
                                       'minuto_actual'])
    """))
    _opt_cols_exist = {row[0] for row in _opt_cols_check}
    for _col in _opt_cols_exist:
        await db.execute(
            text(f"UPDATE partido SET {_col}=NULL WHERE torneo_id=:tid"),
            {"tid": torneo_id},
        )

    # 3) Resetear standings de grupos (participacion) a cero
    await db.execute(
        text(f"""
            UPDATE participacion
            SET pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0, clasifica=FALSE
            WHERE fase_id IN (SELECT id FROM fase WHERE torneo_id=:tid AND tipo='grupo')
        """),
        {"tid": torneo_id},
    )

    # 4) Borrar puntaje_detalle (no tiene torneo_id, acceder via partido_id)
    await db.execute(
        text(f"DELETE FROM puntaje_detalle WHERE partido_id IN ({part_subq})"),
        {"tid": torneo_id},
    )

    # 5) Borrar pronósticos globales A-G y sus puntajes
    await db.execute(text("DELETE FROM apuesta_global WHERE torneo_id=:tid"), {"tid": torneo_id})
    await db.execute(text("DELETE FROM puntaje_global  WHERE torneo_id=:tid"), {"tid": torneo_id})

    # 6) Resetear bracket KO a TBD
    try:
        await _resetear_ko_a_tbd(db, torneo_id)
    except Exception as _e:
        log.warning("reset_torneo.ko_tbd_skip", error=str(_e))

    # 7) Commit antes de recrear placeholders (libera locks)
    await db.commit()

    # 8) Recrear filas apuesta vacías (puntos=0) para cada apostador × partido de grupos
    #    Permite que los apostadores aparezcan en ranking aunque aún no hayan apostado
    placeholders = 0
    rg = await db.execute(
        text("""
            SELECT p.id FROM partido p
            JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
            WHERE p.torneo_id = :tid
        """),
        {"tid": torneo_id},
    )
    grupo_pids = [row[0] for row in rg]
    if grupo_pids:
        async with _app_engine.connect() as conn:
            ar = await conn.execute(text("""
                SELECT u.id FROM users u
                JOIN user_roles ur ON ur.user_id = u.id
                JOIN roles ro ON ro.id = ur.role_id
                WHERE ro.name = 'apostador' AND u.is_active = TRUE
            """))
            apostador_ids = [row[0] for row in ar]
        for uid in apostador_ids:
            res = await db.execute(
                text("""
                    INSERT INTO apuesta (apostador_id, partido_id, puntos, puntos_bonus)
                    SELECT :uid, pid, 0, 0
                    FROM unnest(CAST(:pids AS bigint[])) AS pid
                    ON CONFLICT (apostador_id, partido_id)
                    DO UPDATE SET puntos=0, puntos_bonus=0
                """),
                {"uid": uid, "pids": grupo_pids},
            )
            placeholders += res.rowcount or 0
        await db.commit()

    # 9) Recalcular standings reales desde cero (confirmar todo en 0)
    try:
        await _recalc_participacion(db, torneo_id)
        await db.commit()
    except Exception:
        await db.rollback()

    await _audit_log("reset:torneo", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/reset-torneo/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={"evento": "RESET TOTAL del torneo (superadmin)",
                              "apuestas_borradas": apuestas_borradas,
                              "placeholders_recreados": placeholders})
    return {
        "ok": True,
        "torneo_id":         torneo_id,
        "apuestas_borradas": apuestas_borradas,
        "placeholders":      placeholders,
        "msg":               "Reset completo: resultados, puntajes, bracket y pronósticos borrados.",
    }


@router.api_route("/verificar-registros/{torneo_id}", methods=["GET", "POST"],
                  summary="Verifica (y opcionalmente repara) que todos los apostadores tengan registros de apuesta completos")
async def verificar_registros(torneo_id: int, current: CurrentUser, db: DBSession,
                              reparar: bool = False) -> dict:
    """Algoritmo de consistencia de registros de apuesta.

    Para garantizar que CADA apostador activo esté habilitado para apostar
    (incluso después de un reset, donde se borran las apuestas), verifica que
    exista una fila en `apuesta` por cada partido de la fase de grupos para
    cada apostador. Con ?reparar=true (o POST), crea las filas faltantes como
    placeholders (predicción NULL = registro habilitado, pendiente de completar).
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    # 1) Partidos de la fase de grupos del torneo (set universal a apostar)
    rp = await db.execute(
        text("""
            SELECT p.id FROM partido p
            JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
            WHERE p.torneo_id = :tid
            ORDER BY p.id
        """),
        {"tid": torneo_id},
    )
    partido_ids = [row[0] for row in rp]
    total_partidos = len(partido_ids)
    if total_partidos == 0:
        raise HTTPException(404, "No hay partidos de grupo en este torneo")

    # 2) Apostadores activos (rol 'apostador') desde app_db
    async with _app_engine.connect() as conn:
        ar = await conn.execute(text("""
            SELECT u.id, u.username FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles ro ON ro.id = ur.role_id
            WHERE ro.name = 'apostador' AND u.is_active = TRUE
            ORDER BY u.username
        """))
        apostadores = {row["id"]: row["username"] for row in ar.mappings()}

    # 3) Registros existentes por apostador para esos partidos
    re_ = await db.execute(
        text("""
            SELECT apostador_id, COUNT(*)::int AS n
            FROM apuesta
            WHERE partido_id = ANY(:pids)
            GROUP BY apostador_id
        """),
        {"pids": partido_ids},
    )
    existentes = {row["apostador_id"]: row["n"] for row in re_.mappings()}

    # 4) Diagnóstico + (opcional) reparación
    detalle = []
    creados_total = 0
    for uid, uname in apostadores.items():
        tiene = existentes.get(uid, 0)
        faltan = total_partidos - tiene
        creados = 0
        if reparar and faltan > 0:
            res = await db.execute(
                text("""
                    INSERT INTO apuesta (apostador_id, partido_id)
                    SELECT :uid, pid FROM unnest(CAST(:pids AS bigint[])) AS pid
                    ON CONFLICT (apostador_id, partido_id) DO NOTHING
                """),
                {"uid": uid, "pids": partido_ids},
            )
            creados = res.rowcount or 0
            creados_total += creados
        detalle.append({
            "apostador_id": uid, "nombre": uname,
            "registros": tiene, "esperados": total_partidos,
            "faltantes": faltan, "creados": creados,
            "completo": (tiene + creados) >= total_partidos,
        })

    if reparar:
        await db.commit()
        await _audit_log("registros:reparacion", "bets", current=current, method="POST",
                         path=f"/api/v1/bets/verificar-registros/{torneo_id}",
                         resource_id=str(torneo_id),
                         details={"evento": "habilitación de registros de apuesta",
                                  "registros_creados": creados_total,
                                  "apostadores": len(apostadores)})

    incompletos = [d for d in detalle if not d["completo"]]
    return {
        "ok": True,
        "torneo_id": torneo_id,
        "reparado": reparar,
        "total_apostadores": len(apostadores),
        "partidos_grupo": total_partidos,
        "registros_creados": creados_total,
        "apostadores_incompletos": len(incompletos),
        "detalle": sorted(detalle, key=lambda x: (x["completo"], x["nombre"].lower())),
    }


@router.get("/monitor-dashboard/{torneo_id}", summary="Dashboard completo para panel de mando admin")
async def monitor_dashboard(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Un solo call que devuelve todo lo necesario para el panel de mando del admin:
      - stats: total apostadores, líder, último
      - top5: top 5 del ranking con puntos
      - sin_apuestas: apostadores con apuestas incompletas en fases abiertas
      - partido_activo: partidos en ventana activa (±5 min / 150 min)
      - fases: estado de todas las fases (total, finalizados, bloqueada)
      - mensajes_recientes: últimos 3 mensajes enviados
      - torneo: nombre, api_season, api_league_id, período
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    result: dict = {}

    # ── Torneo info ───────────────────────────────────────────────────────────
    try:
        r_t = await db.execute(
            text("""
                SELECT t.id, t.nombre, t.api_season, t.apuesta_inicio, t.apuesta_fin,
                       c.nombre AS comp_nombre, c.api_league_id
                FROM torneo t
                LEFT JOIN competicion c ON c.id = t.competicion_id
                WHERE t.id = :tid
            """),
            {"tid": torneo_id},
        )
        tor = dict(r_t.mappings().first() or {})
        for f in ("apuesta_inicio", "apuesta_fin"):
            if tor.get(f) and hasattr(tor[f], "isoformat"):
                tor[f] = tor[f].isoformat()
        result["torneo"] = tor
    except Exception:
        await db.rollback()
        result["torneo"] = {}

    # ── Fases estado ──────────────────────────────────────────────────────────
    try:
        r_f = await db.execute(
            text("""
                SELECT f.id, f.nombre, f.tipo, f.orden,
                       COALESCE(f.bloqueada, FALSE) AS bloqueada,
                       COUNT(p.id) AS total,
                       SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END) AS finalizados
                FROM fase f
                LEFT JOIN partido p ON p.fase_id = f.id AND p.torneo_id = :tid
                WHERE f.torneo_id = :tid
                GROUP BY f.id ORDER BY f.orden, f.nombre
            """),
            {"tid": torneo_id},
        )
        result["fases"] = [dict(row) for row in r_f.mappings()]
    except Exception:
        await db.rollback()
        result["fases"] = []

    # ── Partido activo ────────────────────────────────────────────────────────
    try:
        r_pa = await db.execute(
            text("""
                SELECT p.id, p.fecha, p.estado, f.tipo AS fase_tipo, f.nombre AS fase_nombre,
                       COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                       COALESCE(ev.nombre_es, ev.nombre) AS visitante_nombre,
                       p.goles_local, p.goles_visitante
                FROM partido p
                JOIN fase f ON f.id = p.fase_id
                LEFT JOIN equipo el ON el.id = p.equipo_local_id
                LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE p.torneo_id = :tid
                  AND p.estado != 'finalizado'
                  AND p.fecha IS NOT NULL
                  AND p.fecha <= (NOW() AT TIME ZONE 'UTC') + INTERVAL '30 minutes'
                  AND p.fecha >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '150 minutes'
                ORDER BY p.fecha
            """),
            {"tid": torneo_id},
        )
        partidos_activos = []
        for row in r_pa.mappings():
            d = dict(row)
            if d.get("fecha") and hasattr(d["fecha"], "isoformat"):
                d["fecha"] = d["fecha"].isoformat()
            partidos_activos.append(d)
        result["partidos_activos"] = partidos_activos
    except Exception:
        await db.rollback()
        result["partidos_activos"] = []

    # ── Apostadores sin apuestas completas ────────────────────────────────────
    try:
        # Partidos en fases abiertas (no bloqueadas, no finalizados)
        r_pend = await db.execute(
            text("""
                SELECT f.tipo AS fase_tipo, f.nombre AS fase_nombre,
                       COUNT(p.id) AS partidos_pendientes
                FROM partido p
                JOIN fase f ON f.id = p.fase_id
                WHERE p.torneo_id = :tid
                  AND p.estado != 'finalizado'
                  AND COALESCE(f.bloqueada, FALSE) = FALSE
                GROUP BY f.id ORDER BY f.orden, f.nombre
            """),
            {"tid": torneo_id},
        )
        fases_abiertas_info = [dict(r) for r in r_pend.mappings()]
        total_pendientes = sum(f["partidos_pendientes"] for f in fases_abiertas_info)

        # Apuestas realizadas en esos partidos por apostador
        r_apost = await db.execute(
            text("""
                SELECT a.apostador_id, COUNT(*) AS apuestas_hechas
                FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                JOIN fase f ON f.id = p.fase_id
                WHERE p.torneo_id = :tid
                  AND p.estado != 'finalizado'
                  AND COALESCE(f.bloqueada, FALSE) = FALSE
                GROUP BY a.apostador_id
            """),
            {"tid": torneo_id},
        )
        apuestas_map = {row["apostador_id"]: row["apuestas_hechas"] for row in r_apost.mappings()}
    except Exception:
        await db.rollback()
        fases_abiertas_info = []
        total_pendientes    = 0
        apuestas_map        = {}

    # Cruzar con usuarios (app_db)
    sin_apuestas = []
    if total_pendientes > 0:
        async with _app_engine.connect() as conn:
            ar = await conn.execute(
                text("""
                    SELECT u.id, u.username
                    FROM users u
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles ro ON ro.id = ur.role_id
                    WHERE ro.name = 'apostador' AND u.is_active = TRUE
                    ORDER BY u.username
                """)
            )
            todos = [dict(r) for r in ar.mappings()]
        for u in todos:
            hechas = apuestas_map.get(u["id"], 0)
            if hechas < total_pendientes:
                sin_apuestas.append({
                    "nombre":    u["username"],
                    "hechas":    hechas,
                    "pendientes": total_pendientes,
                    "pct":       round(100 * hechas / total_pendientes) if total_pendientes else 0,
                })
        sin_apuestas.sort(key=lambda x: x["hechas"])
    result["sin_apuestas"]        = sin_apuestas
    result["fases_abiertas_info"] = fases_abiertas_info
    result["total_pendientes"]    = total_pendientes

    # ── Top 5 ranking ─────────────────────────────────────────────────────────
    try:
        r_rk = await db.execute(
            text("""
                SELECT a.apostador_id,
                       (COALESCE(SUM(a.puntos),0) + COALESCE(SUM(a.puntos_bonus),0))::int AS pts_partidos,
                       SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3=0  THEN 1 ELSE 0 END)::int AS plenos,
                       SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3<>0 THEN 1 ELSE 0 END)::int AS aciertos
                FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                WHERE p.torneo_id = :tid
                GROUP BY a.apostador_id
                ORDER BY pts_partidos DESC
                LIMIT 5
            """),
            {"tid": torneo_id},
        )
        top_rows = [dict(r) for r in r_rk.mappings()]
        # Globales
        r_glob = await db.execute(
            text("SELECT apostador_id, pts_total FROM puntaje_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        glob_map = {r["apostador_id"]: r["pts_total"] for r in r_glob.mappings()}
        for row in top_rows:
            row["pts_globales"] = glob_map.get(row["apostador_id"], 0) or 0
            row["pts_total"]    = row["pts_partidos"] + row["pts_globales"]

        top_ids = [r["apostador_id"] for r in top_rows]
        if top_ids:
            async with _app_engine.connect() as conn:
                ur = await conn.execute(
                    text("SELECT id, username FROM users WHERE id = ANY(:ids)"),
                    {"ids": top_ids},
                )
                name_map = {r["id"]: r["username"] for r in ur.mappings()}
            for row in top_rows:
                row["nombre"] = name_map.get(row["apostador_id"], f"#{row['apostador_id']}")

        top_rows.sort(key=lambda r: -r["pts_total"])
        result["top5"] = top_rows
    except Exception:
        await db.rollback()
        result["top5"] = []

    # ── Stats generales ───────────────────────────────────────────────────────
    try:
        r_stats = await db.execute(
            text("""
                SELECT
                  COUNT(*)::int                                                               AS total_apuestas,
                  SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3=0  THEN 1 ELSE 0 END)::int AS plenos,
                  SUM(CASE WHEN p.estado='finalizado' AND a.puntos>0 AND a.puntos%3<>0 THEN 1 ELSE 0 END)::int AS aciertos,
                  SUM(CASE WHEN p.estado='finalizado' AND a.puntos=0  THEN 1 ELSE 0 END)::int AS fallos,
                  SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END)::int                AS apuestas_resueltas
                FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                WHERE p.torneo_id = :tid
            """),
            {"tid": torneo_id},
        )
        stats = dict(r_stats.mappings().first() or {})
        # Total apostadores activos
        async with _app_engine.connect() as conn:
            r_ap = await conn.execute(
                text("""
                    SELECT COUNT(*)::int AS total FROM users u
                    JOIN user_roles ur ON ur.user_id = u.id
                    JOIN roles r ON r.id = ur.role_id
                    WHERE r.name='apostador' AND u.is_active=TRUE
                """)
            )
            stats["total_apostadores"] = r_ap.scalar() or 0
        result["stats"] = stats
    except Exception:
        await db.rollback()
        result["stats"] = {}

    # ── Mensajes recientes ────────────────────────────────────────────────────
    try:
        r_msg = await db.execute(
            text("""
                SELECT id, titulo, contenido, created_at
                FROM mensaje_admin
                WHERE torneo_id = :tid
                ORDER BY created_at DESC LIMIT 3
            """),
            {"tid": torneo_id},
        )
        mensajes = []
        for row in r_msg.mappings():
            d = dict(row)
            if d.get("created_at") and hasattr(d["created_at"], "isoformat"):
                d["created_at"] = d["created_at"].isoformat()
            mensajes.append(d)
        result["mensajes_recientes"] = mensajes
    except Exception:
        await db.rollback()
        result["mensajes_recientes"] = []

    return result


@router.get("/partidos-hoy/{torneo_id}", summary="Partidos del día actual con marcador (sin auth)")
async def partidos_hoy(torneo_id: int, db: DBSession, fecha: str = None) -> list[dict]:
    """
    Devuelve todos los partidos del día (parámetro fecha=YYYY-MM-DD, por defecto hoy)
    con estado, marcador y datos de equipo. Sin autenticación — lectura pública.
    """
    from datetime import date, timedelta, datetime
    try:
        target = date.fromisoformat(fecha) if fecha else date.today()
    except ValueError:
        target = date.today()
    # Ventana amplia: cubre cualquier timezone del mundo (UTC-12 a UTC+14).
    # IMPORTANTE: convertir a datetime ANTES de aplicar timedelta con horas;
    # date - timedelta(hours=N) ignora las horas (solo usa .days), dejando
    # una ventana de 1 día que excluye partidos nocturnos en UTC.
    target_dt = datetime(target.year, target.month, target.day)
    desde = target_dt - timedelta(hours=14)   # cubre UTC+14 (línea de fecha)
    hasta = target_dt + timedelta(hours=38)   # cubre UTC-12 + 2h de margen

    rp = await db.execute(
        text("""
            SELECT p.id, p.estado, f.tipo AS fase_tipo,
                   p.fecha,
                   p.goles_local, p.goles_visitante,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   el.logo_url AS local_logo,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre,
                   ev.logo_url AS visit_logo
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid
              AND p.fecha >= :desde AND p.fecha < :hasta
            ORDER BY p.fecha
        """),
        {"tid": torneo_id, "desde": desde, "hasta": hasta},
    )
    result = []
    for r in rp.mappings():
        d = dict(r)
        if d.get("fecha") and hasattr(d["fecha"], "isoformat"):
            d["fecha"] = d["fecha"].isoformat()
        result.append(d)
    return result


@router.post("/finalizar-partido/{partido_id}", summary="Admin: finalizar partido manualmente y recalcular puntajes (emergencia)")
async def finalizar_partido_manual(
    partido_id: int,
    current: CurrentUser,
    db: DBSession,
    goles_local: int = Query(..., ge=0, le=30, description="Goles del equipo local"),
    goles_visitante: int = Query(..., ge=0, le=30, description="Goles del equipo visitante"),
    penales_local: int | None = Query(None, ge=0, le=30, description="Penales tanda local (opcional, solo si hubo tanda)"),
    penales_visitante: int | None = Query(None, ge=0, le=30, description="Penales tanda visitante (opcional)"),
) -> dict:
    """
    Fuerza el cierre de un partido cuando la API externa queda trabada.
    1. Actualiza partido: goles, estado='finalizado', penales tanda, equipo_clasificado_id.
    2. Recalcula standings (PJ/PG/PE/PP/GF/GC/Pts).
    3. Avanza bracket (asigna ganadores a siguiente fase).
    4. Recalcula puntajes de apostadores.
    Solo admin/superadmin.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    # ── Cargar partido ────────────────────────────────────────────────────────
    rp = await db.execute(
        text("""
            SELECT p.id, p.torneo_id, p.fase_id, p.equipo_local_id, p.equipo_visitante_id,
                   p.estado, p.goles_local, p.goles_visitante,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visitante_nombre,
                   f.tipo AS fase_tipo
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.id = :pid
        """),
        {"pid": partido_id},
    )
    row = rp.mappings().fetchone()
    if not row:
        raise HTTPException(404, f"Partido {partido_id} no encontrado")

    torneo_id = row["torneo_id"]
    fase_tipo  = row["fase_tipo"]

    # ── Determinar equipo_clasificado_id (KO: ganador por goles o penales tanda) ──
    equipo_clasificado_id = None
    if fase_tipo != "grupo":
        if goles_local != goles_visitante:
            equipo_clasificado_id = row["equipo_local_id"] if goles_local > goles_visitante else row["equipo_visitante_id"]
        elif penales_local is not None and penales_visitante is not None:
            equipo_clasificado_id = row["equipo_local_id"] if penales_local > penales_visitante else row["equipo_visitante_id"]

    # ── UPDATE partido ────────────────────────────────────────────────────────
    await db.execute(
        text("""
            UPDATE partido
            SET goles_local           = :gl,
                goles_visitante       = :gv,
                estado                = 'finalizado',
                penales_local         = :pl,
                penales_visitante     = :pv,
                equipo_clasificado_id = COALESCE(:ecid, equipo_clasificado_id),
                minuto_actual         = NULL
            WHERE id = :pid
        """),
        {
            "gl":   goles_local,
            "gv":   goles_visitante,
            "pl":   penales_local,
            "pv":   penales_visitante,
            "ecid": equipo_clasificado_id,
            "pid":  partido_id,
        },
    )
    await db.commit()

    # ── Cadena de recálculo ───────────────────────────────────────────────────
    recap: dict = {}

    # 1. Standings de grupos
    try:
        await _recalc_participacion(db, torneo_id)
        await db.commit()
        recap["standings_ok"] = True
    except Exception as e:
        recap["standings_error"] = str(e)

    # 2. Avanzar bracket KO
    try:
        maps = await ko_scoring.build_num_maps(db, torneo_id)
        await _avanzar_bracket(db, torneo_id, maps)
        await db.commit()
        recap["bracket_ok"] = True
    except Exception as e:
        recap["bracket_error"] = str(e)

    # 3. Calcular puntajes apostadores
    try:
        from app.services.scoring.registry import get_engine as _get_engine
        from app.services.scoring.calculator import ScoringCalculator
        rc = await db.execute(
            text("SELECT c.codigo FROM competicion c JOIN torneo t ON t.competicion_id=c.id WHERE t.id=:tid"),
            {"tid": torneo_id},
        )
        comp_row = rc.mappings().fetchone()
        engine = _get_engine(comp_row["codigo"] if comp_row else None)
        result = await ScoringCalculator(db).calculate(torneo_id, engine)
        await ScoringCalculator(db).calculate_global(torneo_id, engine)
        await db.commit()
        recap["puntajes_ok"] = True
        recap["puntajes_procesados"] = result.get("apostadores_procesados", 0)
    except Exception as e:
        recap["puntajes_error"] = str(e)

    await _audit_log(
        f"finalizar_partido_manual:{partido_id}:{goles_local}-{goles_visitante}",
        "bets", current=current, method="POST",
        detail={"partido_id": partido_id, "goles_local": goles_local,
                "goles_visitante": goles_visitante, "penales_local": penales_local,
                "penales_visitante": penales_visitante, "equipo_clasificado_id": equipo_clasificado_id},
    )

    return {
        "ok": True,
        "partido_id": partido_id,
        "partido": f"{row['local_nombre']} {goles_local}–{goles_visitante} {row['visitante_nombre']}",
        "estado": "finalizado",
        "equipo_clasificado_id": equipo_clasificado_id,
        **recap,
    }


@router.get("/hay-partido-activo/{torneo_id}", summary="¿Hay algún partido activo o por empezar? (para sync automático)")
async def hay_partido_activo(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Devuelve {activo: bool, partidos: [...]} para que el sync automático
    decida si debe correr o no.

    Un partido es "activo" si:
      - Empezó hace entre 15 y 210 minutos (sync arranca al min 15 del primer tiempo)
      - Y su estado NO es 'finalizado'

    La ventana empieza en +15 min para evitar calls a la API antes de que haya
    datos de eventos disponibles. 210 min cubre 90 min regulares + alargue + penales.

    Usado por sync_auto.py: si activo=false, el script sale sin hacer ninguna llamada a API-Football.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    r = await db.execute(
        text("""
            SELECT p.id, p.fecha, p.estado,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visitante_nombre,
                   f.tipo AS fase_tipo
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid
              AND p.estado != 'finalizado'
              AND p.fecha IS NOT NULL
              AND (
                -- Ventana temporal normal (min 15 a 300 desde inicio)
                (p.fecha <= (NOW() AT TIME ZONE 'UTC') - INTERVAL '15 minutes'
                 AND p.fecha >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '300 minutes')
                OR
                -- Partido ya marcado en_juego en BD: sincronizar siempre hasta que finalice
                p.estado = 'en_juego'
              )
            ORDER BY p.fecha
        """),
        {"tid": torneo_id},
    )
    partidos = []
    for row in r.mappings():
        d = dict(row)
        if d.get("fecha"):
            d["fecha"] = d["fecha"].isoformat() if hasattr(d["fecha"], "isoformat") else str(d["fecha"])
        partidos.append(d)

    return {
        "activo":   len(partidos) > 0,
        "partidos": partidos,
        "total":    len(partidos),
    }


@router.get("/partidos-en-vivo/{torneo_id}", summary="Partidos activos hoy con datos live (score, cards, VAR…)")
async def partidos_en_vivo(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Devuelve los partidos de hoy + en juego ahora + finalizados en las últimas 3h,
    con todos los campos actualizados por el sync (score, amarillas, rojas, VAR,
    minuto_primer_gol, penales tanda, estado, minuto_actual).
    Diseñado para el tab "En Vivo" con auto-refresh cada 30s en el UI.
    """
    import json as _json

    r = await db.execute(
        text("""
            SELECT
                p.id, p.fecha, p.estado,
                NULL::int AS numero,
                p.goles_local, p.goles_visitante,
                p.penales_local, p.penales_visitante,
                p.amarillas, p.rojas, p.decisiones_var,
                p.minuto_primer_gol,
                p.minuto_actual,
                COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                el.logo_url  AS local_logo,
                COALESCE(ev.nombre_es, ev.nombre) AS visitante_nombre,
                ev.logo_url  AS visitante_logo,
                f.nombre     AS fase_nombre,
                f.tipo       AS fase_tipo,
                p.eventos_api::text      AS eventos_api_raw,
                p.estadisticas_api::text AS estadisticas_api_raw,
                -- predicción del apostador actual
                ap.pred_local, ap.pred_visitante,
                ap.pred_penales_local_tanda, ap.pred_penales_visitante_tanda,
                ap.pred_amarillas, ap.pred_rojas, ap.pred_var, ap.pred_minuto_gol,
                -- puntaje calculado para este partido
                pd.pts_resultado, pd.pts_marcador,
                pd.pts_amarillas, pd.pts_rojas, pd.pts_var, pd.pts_minuto,
                pd.pts_penales_tanda,
                (COALESCE(pd.pts_resultado,0) + COALESCE(pd.pts_marcador,0) +
                 COALESCE(pd.pts_amarillas,0) + COALESCE(pd.pts_rojas,0) +
                 COALESCE(pd.pts_var,0)       + COALESCE(pd.pts_minuto,0) +
                 COALESCE(pd.pts_penales_tanda,0)) AS pts_total
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            LEFT JOIN apuesta ap ON ap.partido_id = p.id AND ap.apostador_id = :uid
            LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = :uid
            WHERE p.torneo_id = :tid
              AND p.fecha IS NOT NULL
              AND (
                  p.estado = 'en_juego'
                  OR DATE(p.fecha AT TIME ZONE 'UTC') = CURRENT_DATE
                  OR (p.estado = 'finalizado'
                      AND p.fecha >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '3 hours')
              )
            ORDER BY
                CASE p.estado
                    WHEN 'en_juego'   THEN 1
                    WHEN 'programado' THEN 2
                    WHEN 'finalizado' THEN 3
                    ELSE 4
                END,
                p.fecha
        """),
        {"tid": torneo_id, "uid": current.id},
    )
    partidos = []
    for row in r.mappings():
        d = dict(row)
        if d.get("fecha") and hasattr(d["fecha"], "isoformat"):
            d["fecha"] = d["fecha"].isoformat()
        # Parsear JSON raw de eventos y estadísticas
        raw_ev = d.pop("eventos_api_raw", None)
        raw_st = d.pop("estadisticas_api_raw", None)
        try:
            d["eventos_api"] = _json.loads(raw_ev) if raw_ev else []
        except Exception:
            d["eventos_api"] = []
        try:
            d["estadisticas_api"] = _json.loads(raw_st) if raw_st else []
        except Exception:
            d["estadisticas_api"] = []
        partidos.append(d)

    return {"partidos": partidos, "total": len(partidos)}


@router.get("/noticias", summary="Noticias del Mundial desde Google News RSS (proxy backend)")
async def get_noticias(
    q: str = "Copa del Mundo 2026 FIFA",
    hl: str = "es",
    gl: str = "MX",
    current: CurrentUser = None,
) -> dict:
    """
    Proxy server-side para Google News RSS.
    Evita problemas CORS del navegador. Devuelve lista de items.
    """
    import xml.etree.ElementTree as ET
    import httpx

    ceid = f"{gl}:{hl}"
    url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; BECBUC-News/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception as e:
        raise HTTPException(502, f"Error al obtener noticias: {e}")

    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return {"items": [], "error": "RSS sin canal"}
        items = []
        for item in channel.findall("item")[:25]:
            title_raw = (item.findtext("title") or "").strip()
            link  = item.findtext("link") or ""
            date  = item.findtext("pubDate") or ""
            # Google News title format: "Article Title - Source Name"
            parts = title_raw.rsplit(" - ", 1)
            title  = parts[0].strip() if len(parts) > 1 else title_raw
            source = parts[1].strip() if len(parts) > 1 else ""
            items.append({"title": title, "source": source, "link": link, "date": date})
        return {"items": items, "query": q}
    except ET.ParseError as e:
        raise HTTPException(502, f"Error al parsear RSS: {e}")


@router.get("/fases-estado/{torneo_id}", summary="Estado de todas las fases del torneo (para consola admin)")
async def fases_estado(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    r = await db.execute(
        text("""
            SELECT
                f.id, f.nombre, f.tipo, f.orden,
                COALESCE(f.visible_apostador, TRUE) AS visible_apostador,
                COUNT(p.id)::int AS total,
                SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END)::int AS finalizados,
                SUM(CASE WHEN p.estado!='finalizado' THEN 1 ELSE 0 END)::int AS pendientes
            FROM fase f
            LEFT JOIN partido p ON p.fase_id = f.id
            WHERE f.torneo_id = :tid
            GROUP BY f.id, f.nombre, f.tipo, f.orden, f.visible_apostador
            ORDER BY f.orden, f.nombre
        """),
        {"tid": torneo_id},
    )
    fases = []
    for row in r.mappings():
        d = dict(row)
        d["concluida"] = d["total"] > 0 and d["pendientes"] == 0
        d["sin_partidos"] = d["total"] == 0
        fases.append(d)

    # Marcar cuál es la "fase activa" sugerida: la primera no concluida con partidos,
    # respetando que la anterior esté concluida.
    fase_activa_id = None
    prev_ok = True
    for f in fases:
        if f["sin_partidos"]:
            continue
        if prev_ok and not f["concluida"]:
            fase_activa_id = f["id"]
            break
        prev_ok = f["concluida"]

    return {"torneo_id": torneo_id, "fases": fases, "fase_activa_sugerida": fase_activa_id}


@router.get("/fases-bloqueo/{torneo_id}",
            summary="Estado de bloqueo manual por fase (admin)")
async def get_fases_bloqueo(torneo_id: int, current: CurrentUser, db: DBSession) -> list[dict]:
    """Devuelve todas las fases del torneo con su estado de bloqueo manual e inicio/fin calculados."""
    r = await db.execute(
        text("""
            SELECT f.id, f.nombre, f.tipo, f.orden,
                   COALESCE(f.bloqueada, FALSE) AS bloqueada,
                   COUNT(p.id)::int AS total,
                   SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END)::int AS finalizados,
                   MIN(p.fecha) AS fecha_inicio,
                   MAX(p.fecha) AS fecha_fin
            FROM fase f
            LEFT JOIN partido p ON p.fase_id = f.id
            WHERE f.torneo_id = :tid
            GROUP BY f.id, f.nombre, f.tipo, f.orden
            ORDER BY f.orden, f.nombre
        """),
        {"tid": torneo_id},
    )
    rows = []
    for row in r.mappings():
        d = dict(row)
        # Serializar fechas
        d["fecha_inicio"] = d["fecha_inicio"].isoformat() if d.get("fecha_inicio") else None
        d["fecha_fin"] = d["fecha_fin"].isoformat() if d.get("fecha_fin") else None
        rows.append(d)
    return rows


@router.patch("/fases-bloqueo-grupo/{torneo_id}",
              summary="Bloquear/desbloquear todas las fases de grupo del torneo (admin)")
async def set_fases_grupo_bloqueo(torneo_id: int, body: dict, current: CurrentUser, db: DBSession) -> dict:
    """Actualiza bloqueada=True/False para TODAS las fases de tipo 'grupo' del torneo."""
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    bloqueada = bool(body.get("bloqueada", False))
    await db.execute(
        text("UPDATE fase SET bloqueada = :b WHERE torneo_id = :tid AND tipo = 'grupo'"),
        {"b": bloqueada, "tid": torneo_id},
    )
    await db.commit()
    await _audit_log("fase:bloqueo_grupo", "bets", current=current, method="PATCH",
                     path=f"/api/v1/bets/fases-bloqueo-grupo/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={"torneo_id": torneo_id, "bloqueada": bloqueada})
    return {"ok": True, "torneo_id": torneo_id, "bloqueada": bloqueada}


@router.patch("/fases-bloqueo/{fase_id}",
              summary="Actualizar bloqueo manual de una fase (admin)")
async def set_fase_bloqueo(fase_id: int, body: dict, current: CurrentUser, db: DBSession) -> dict:
    """Actualiza el campo bloqueada de una fase. body: {bloqueada: bool}"""
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    bloqueada = bool(body.get("bloqueada", False))
    r = await db.execute(
        text("UPDATE fase SET bloqueada = :b WHERE id = :fid RETURNING id, nombre, bloqueada"),
        {"b": bloqueada, "fid": fase_id},
    )
    row = r.mappings().first()
    if not row:
        raise HTTPException(404, "Fase no encontrada")
    await db.commit()
    await _audit_log("fase:bloqueo", "bets", current=current, method="PATCH",
                     path=f"/api/v1/bets/fases-bloqueo/{fase_id}",
                     resource_id=str(fase_id),
                     details={"fase": row["nombre"], "bloqueada": bloqueada})
    return {"ok": True, "fase_id": fase_id, "nombre": row["nombre"], "bloqueada": row["bloqueada"]}


@router.get("/fases-apuesta-estado/{torneo_id}",
            summary="Estado de apuesta por fase (bloqueada/habilitada) para cualquier usuario")
async def fases_apuesta_estado(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """Para cada fase indica si está habilitada o bloqueada para cargar apuestas.
    Bloqueada si: fase.bloqueada=true (manual admin) O fase concluida.
    La fecha del primer partido se muestra como referencia informativa.
    """
    r = await db.execute(
        text("""
            SELECT
                f.id, f.nombre, f.tipo, f.orden,
                COALESCE(f.bloqueada, FALSE) AS bloqueada_manual,
                COUNT(p.id)::int                                              AS total,
                SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END)::int  AS finalizados,
                MIN(p.fecha)                                                  AS fecha_inicio_fase,
                MIN(p.fecha) - INTERVAL '5 hours'                            AS fecha_corte
            FROM fase f
            LEFT JOIN partido p ON p.fase_id = f.id
            WHERE f.torneo_id = :tid
            GROUP BY f.id, f.nombre, f.tipo, f.orden
            ORDER BY f.orden, f.nombre
        """),
        {"tid": torneo_id},
    )
    rows = [dict(x) for x in r.mappings()]

    def _fmt(dt) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return f"{dt.day}/{dt.month}/{dt.year} {dt.strftime('%H:%M')}"

    fases = []
    for d in rows:
        total       = d["total"] or 0
        finalizados = d["finalizados"] or 0
        concluida   = total > 0 and finalizados == total
        bloqueada_manual = d["bloqueada_manual"]
        fecha_corte  = d["fecha_corte"]
        fecha_inicio = d["fecha_inicio_fase"]

        # Normalizar tz
        if fecha_corte is not None and fecha_corte.tzinfo is None:
            fecha_corte = fecha_corte.replace(tzinfo=timezone.utc)
        if fecha_inicio is not None and fecha_inicio.tzinfo is None:
            fecha_inicio = fecha_inicio.replace(tzinfo=timezone.utc)

        if bloqueada_manual:
            bloqueada = True
            motivo    = "Bloqueada manualmente por el administrador"
            icono     = "lock"
        elif concluida:
            bloqueada = True
            motivo    = "Fase concluida — período de apuesta cerrado"
            icono     = "lock"
        else:
            bloqueada = False
            motivo    = f"Abierto · primer partido {_fmt(fecha_inicio)}" if fecha_inicio else "Habilitada para cargar apuestas"
            icono     = "lock-open"

        fases.append({
            "fase_id":       d["id"],
            "nombre":        d["nombre"],
            "tipo":          d["tipo"],
            "orden":         d["orden"],
            "total":         total,
            "finalizados":   finalizados,
            "concluida":     concluida,
            "fecha_inicio":  fecha_inicio.isoformat() if fecha_inicio else None,
            "fecha_corte":   fecha_corte.isoformat()  if fecha_corte  else None,
            "fecha_corte_fmt": _fmt(fecha_corte),
            "bloqueada":     bloqueada,
            "motivo":        motivo,
            "icono":         icono,
        })

    fase_habilitada_id = next((f["fase_id"] for f in fases if not f["bloqueada"]), None)
    return {"torneo_id": torneo_id, "fases": fases, "fase_habilitada_id": fase_habilitada_id}


async def _calc_standings_reales(db: DBSession, torneo_id: int) -> dict:
    """Calcula standings de grupos desde los resultados reales (goles en tabla partido)."""
    r_teams = await db.execute(
        text("""
            SELECT f.id AS fase_id, f.nombre AS fase_nombre,
                   e.id AS equipo_id, e.fifa_ranking,
                   COALESCE(e.nombre_es, e.nombre) AS nombre,
                   e.logo_url,
                   COALESCE(e.codigo_iso, '') AS codigo_iso
            FROM participacion pa
            JOIN equipo e ON e.id = pa.equipo_id
            JOIN fase f ON f.id = pa.fase_id
            WHERE f.torneo_id = :tid AND f.tipo = 'grupo'
        """),
        {"tid": torneo_id},
    )
    grupos: dict[int, dict] = {}
    grupo_nombres: dict[int, str] = {}
    for row in r_teams.mappings():
        fid = row["fase_id"]
        grupo_nombres[fid] = row["fase_nombre"]
        grupos.setdefault(fid, {})[row["equipo_id"]] = {
            "equipo_id": row["equipo_id"],
            "nombre": row["nombre"],
            "logo_url": row["logo_url"],
            "fifa_ranking": row["fifa_ranking"] or 999,
            "fair_play_pts": 0,
            "pj": 0, "pg": 0, "pe": 0, "pp": 0,
            "gf": 0, "gc": 0, "gd": 0, "pts": 0,
        }

    r_parts = await db.execute(
        text("""
            SELECT f.id AS fase_id,
                   p.equipo_local_id, p.equipo_visitante_id,
                   p.goles_local, p.goles_visitante
            FROM partido p
            JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
            WHERE p.torneo_id = :tid AND p.estado = 'finalizado'
              AND p.goles_local IS NOT NULL AND p.goles_visitante IS NOT NULL
        """),
        {"tid": torneo_id},
    )
    for p in r_parts.mappings():
        fid = p["fase_id"]
        lid, vid = p["equipo_local_id"], p["equipo_visitante_id"]
        gl, gv = p["goles_local"], p["goles_visitante"]
        if fid not in grupos or lid not in grupos[fid] or vid not in grupos[fid]:
            continue
        loc, vis = grupos[fid][lid], grupos[fid][vid]
        loc["pj"] += 1; vis["pj"] += 1
        loc["gf"] += gl; vis["gf"] += gv
        loc["gc"] += gv; vis["gc"] += gl
        loc["gd"] += gl - gv; vis["gd"] += gv - gl
        if gl > gv:
            loc["pg"] += 1; loc["pts"] += 3; vis["pp"] += 1
        elif gl == gv:
            loc["pe"] += 1; loc["pts"] += 1; vis["pe"] += 1; vis["pts"] += 1
        else:
            vis["pg"] += 1; vis["pts"] += 3; loc["pp"] += 1

    result = {}
    for fid, teams in grupos.items():
        sorted_teams = sorted(
            teams.values(),
            key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["fifa_ranking"]),
        )
        nombre = grupo_nombres[fid]
        grupo_letra = nombre.replace("Grupo ", "").strip()
        for idx, eq in enumerate(sorted_teams):
            eq["pos"] = idx + 1
            eq["grupo"] = grupo_letra
        # Estructura {"equipos": [...]} para compatibilidad con seleccionar_mejores_terceros
        result[grupo_letra] = {"fase_id": fid, "grupo": grupo_letra, "equipos": sorted_teams}
    return result


async def _recalc_participacion(db: DBSession, torneo_id: int) -> int:
    """Recalcula la tabla participacion (cuadro de grupos: PJ/PG/PE/PP/GF/GC/Pts/posicion)
    desde los resultados reales en la tabla partido. Idempotente.
    Devuelve el nº de filas actualizadas."""
    standings = await _calc_standings_reales(db, torneo_id)
    actualizadas = 0
    for grupo in standings.values():
        fase_id = grupo.get("fase_id")
        for eq in grupo.get("equipos", []):
            await db.execute(
                text("""
                    UPDATE participacion
                    SET pj=:pj, pg=:pg, pe=:pe, pp=:pp,
                        gf=:gf, gc=:gc, pts=:pts,
                        posicion=:pos, clasifica=:clasifica
                    WHERE fase_id=:fid AND equipo_id=:eid
                """),
                {
                    "pj": eq["pj"], "pg": eq["pg"], "pe": eq["pe"], "pp": eq["pp"],
                    "gf": eq["gf"], "gc": eq["gc"], "pts": eq["pts"],
                    "pos": eq["pos"], "clasifica": eq["pos"] <= 2,
                    "fid": fase_id, "eid": eq["equipo_id"],
                },
            )
            actualizadas += 1
    return actualizadas


async def _ensure_detalle_table(db):
    """Crea la tabla de detalle de puntaje por partido/fase/item si no existe."""
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS puntaje_detalle (
            id              SERIAL PRIMARY KEY,
            torneo_id       INT NOT NULL,
            fase_id         INT NOT NULL,
            fase_tipo       VARCHAR(30) NOT NULL,
            fase_nombre     VARCHAR(80),
            partido_id      INT NOT NULL,
            apostador_id    INT NOT NULL,
            multiplicador   INT NOT NULL DEFAULT 1,
            pred_local      INT, pred_visitante INT,
            real_local      INT, real_visitante INT,
            pts_marcador_base  INT NOT NULL DEFAULT 0,
            pts_marcador       INT NOT NULL DEFAULT 0,
            pred_minuto     INT, real_minuto INT, gano_minuto BOOLEAN DEFAULT FALSE,
            pts_minuto      INT NOT NULL DEFAULT 0,
            pred_amarillas  INT, real_amarillas INT,
            pts_amarillas   INT NOT NULL DEFAULT 0,
            pred_var        INT, real_var INT,
            pts_var         INT NOT NULL DEFAULT 0,
            pts_bonus       INT NOT NULL DEFAULT 0,
            pts_total       INT NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE (torneo_id, partido_id, apostador_id)
        )
    """))


# ── Pronósticos globales A-G ─────────────────────────────────────────────────

@router.post("/apuestas-globales/{torneo_id}", summary="Guardar pronósticos globales A-G del apostador")
async def guardar_apuestas_globales(
    torneo_id: int,
    body: dict,
    current: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Upsert de los pronósticos globales (A-G) del apostador autenticado.
    Campos aceptados: pred_campeon_id, pred_finalista1_id, pred_finalista2_id,
    pred_goleador, pred_peor_equipo_id, pred_goleada_ganador, pred_goleada_perdedor,
    pred_etapa_paraguay, pred_goles_paraguay.
    """
    uid = current.id
    await db.execute(
        text("""
            INSERT INTO apuesta_global
              (torneo_id, apostador_id,
               pred_campeon_id, pred_finalista1_id, pred_finalista2_id,
               pred_goleador, pred_peor_equipo_id,
               pred_goleada_ganador, pred_goleada_perdedor,
               pred_etapa_paraguay, pred_goles_paraguay,
               updated_at)
            VALUES
              (:tid, :uid,
               :campeon, :fin1, :fin2,
               :goleador, :peor,
               :gol_g, :gol_p,
               :etapa, :goles,
               NOW())
            ON CONFLICT (torneo_id, apostador_id) DO UPDATE SET
               pred_campeon_id      = EXCLUDED.pred_campeon_id,
               pred_finalista1_id   = EXCLUDED.pred_finalista1_id,
               pred_finalista2_id   = EXCLUDED.pred_finalista2_id,
               pred_goleador        = EXCLUDED.pred_goleador,
               pred_peor_equipo_id  = EXCLUDED.pred_peor_equipo_id,
               pred_goleada_ganador = EXCLUDED.pred_goleada_ganador,
               pred_goleada_perdedor= EXCLUDED.pred_goleada_perdedor,
               pred_etapa_paraguay  = EXCLUDED.pred_etapa_paraguay,
               pred_goles_paraguay  = EXCLUDED.pred_goles_paraguay,
               updated_at           = NOW()
        """),
        {
            "tid":     torneo_id,
            "uid":     uid,
            "campeon": body.get("pred_campeon_id"),
            "fin1":    body.get("pred_finalista1_id"),
            "fin2":    body.get("pred_finalista2_id"),
            "goleador":body.get("pred_goleador"),
            "peor":    body.get("pred_peor_equipo_id"),
            "gol_g":   body.get("pred_goleada_ganador"),
            "gol_p":   body.get("pred_goleada_perdedor"),
            "etapa":   body.get("pred_etapa_paraguay"),
            "goles":   body.get("pred_goles_paraguay"),
        },
    )
    await db.commit()
    return {"ok": True, "torneo_id": torneo_id, "apostador_id": uid}


@router.get("/apuestas-globales/{torneo_id}", summary="Leer pronósticos globales A-G del apostador")
async def leer_apuestas_globales(
    torneo_id: int,
    current: CurrentUser,
    db: DBSession,
    for_apostador_id: int = None,
) -> dict:
    """
    Devuelve los pronósticos globales del apostador autenticado para el torneo.
    Incluye los puntajes ya calculados (si existen en puntaje_global).
    Admin puede pasar for_apostador_id para ver pronósticos de otro apostador.
    """
    uid = current.id
    if for_apostador_id and await _check_admin(current):
        uid = for_apostador_id
    r = await db.execute(
        text("SELECT * FROM apuesta_global WHERE torneo_id = :tid AND apostador_id = :uid"),
        {"tid": torneo_id, "uid": uid},
    )
    ag = r.mappings().first()

    rp = await db.execute(
        text("SELECT * FROM puntaje_global WHERE torneo_id = :tid AND apostador_id = :uid"),
        {"tid": torneo_id, "uid": uid},
    )
    pg = rp.mappings().first()

    return {
        "apuesta_global":  dict(ag)  if ag else {},
        "puntaje_global":  dict(pg)  if pg else {},
    }


@router.post("/resultados-globales/{torneo_id}",
             summary="Establecer resultados globales C/D para scoring (admin)")
async def set_resultados_globales(
    torneo_id: int,
    body: dict,
    current: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Admin establece los resultados de los ítems que no son auto-computables:
      C: resultado_goleador (nombre del jugador, texto)
      D: resultado_peor_equipo_id (equipo_id del peor equipo en grupos)
    Agrega las columnas al torneo si no existen (idempotente).
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    for col_sql in [
        "ALTER TABLE torneo ADD COLUMN IF NOT EXISTS resultado_goleador VARCHAR(100)",
        "ALTER TABLE torneo ADD COLUMN IF NOT EXISTS resultado_peor_equipo_id INT",
    ]:
        try:
            await db.execute(text(col_sql))
        except Exception:
            await db.rollback()

    updates = []
    params: dict = {"tid": torneo_id}
    if "resultado_goleador" in body:
        updates.append("resultado_goleador = :goleador")
        params["goleador"] = body["resultado_goleador"]
    if "resultado_peor_equipo_id" in body:
        updates.append("resultado_peor_equipo_id = :peor_eq")
        params["peor_eq"] = body["resultado_peor_equipo_id"]

    if updates:
        await db.execute(
            text(f"UPDATE torneo SET {', '.join(updates)} WHERE id = :tid"),
            params,
        )
        await db.commit()

    return {"ok": True, "torneo_id": torneo_id, "campos_actualizados": list(params.keys() - {"tid"})}


@router.post("/calcular-puntajes/{torneo_id}", summary="Calcular puntajes según reglamento oficial por competencia (admin)")
async def calcular_puntajes(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    await _ensure_detalle_table(db)

    # ── Columnas puntaje_detalle (idempotente, compatibilidad v1 + v2) ───────
    for col_sql in [
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS teams_match BOOLEAN DEFAULT TRUE",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pred_penales BOOLEAN",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS real_penales BOOLEAN",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales INT NOT NULL DEFAULT 0",
        # Columnas v2 (GRUPO 0)
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_resultado INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_rojas INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_tanda INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_equipo INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_partido INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_penales_tanda INT DEFAULT 0",
        "ALTER TABLE puntaje_detalle ADD COLUMN IF NOT EXISTS pts_rojas INT DEFAULT 0",
        # Columnas globales en torneo (para scoring C/D — se crean si no existen)
        # IMPORTANTE: deben existir ANTES de que _load_torneo_resultados las consulte,
        # de lo contrario el SELECT falla y deja la transacción en estado aborted.
        "ALTER TABLE torneo ADD COLUMN IF NOT EXISTS resultado_goleador VARCHAR(100)",
        "ALTER TABLE torneo ADD COLUMN IF NOT EXISTS resultado_peor_equipo_id INT",
    ]:
        try:
            await db.execute(text(col_sql))
        except Exception:
            pass  # ADD COLUMN IF NOT EXISTS no debería fallar; no corromper la sesión

    # ── Resolver engine según competicion.codigo del torneo ──────────────────
    r_torneo = await db.execute(
        text("""
            SELECT t.id, COALESCE(c.codigo, '') AS competicion_codigo
            FROM torneo t
            LEFT JOIN competicion c ON c.id = t.competicion_id
            WHERE t.id = :tid
        """),
        {"tid": torneo_id},
    )
    row_torneo = r_torneo.mappings().first()
    if not row_torneo:
        raise HTTPException(404, f"Torneo {torneo_id} no encontrado.")
    competicion_codigo = row_torneo["competicion_codigo"] or None
    engine = scoring_registry.get_engine(competicion_codigo)

    # ── Delegar puntajes partido a partido ───────────────────────────────────
    calc = ScoringCalculator(db)
    result = await calc.calculate(torneo_id, engine)
    if result is None:
        raise HTTPException(400, "No hay partidos finalizados. Ejecutá 'Simular resultados' primero.")

    plenos   = result["plenos"]
    aciertos = result["aciertos"]
    fallos   = result["fallos"]
    por_fase = result["por_fase"]

    # ── Puntajes globales A-G (si hay apuestas globales) ─────────────────────
    global_result = await calc.calculate_global(torneo_id, engine)
    globales_procesadas = global_result.get("procesadas", 0)

    await db.commit()
    await _audit_log("puntajes:calculo", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/calcular-puntajes/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={
                         "evento": "cálculo de puntajes",
                         "engine": competicion_codigo or "default",
                         "plenos": plenos, "aciertos": aciertos, "fallos": fallos,
                         "globales_procesadas": globales_procesadas,
                     })
    return {
        "ok":      True,
        "engine":  competicion_codigo or "default",
        "plenos":  plenos,
        "aciertos": aciertos,
        "fallos":  fallos,
        "por_fase": por_fase,
        "globales_procesadas": globales_procesadas,
    }


@router.post("/sync-resultados/{torneo_id}", summary="Sincronizar resultados desde API-Football (admin)")
async def sync_resultados(
    torneo_id: int,
    current: CurrentUser,
    db: DBSession,
    force: bool = False,
    max_detalle: int = 10,
    reset_resultados: bool = False,
) -> dict:
    """
    Cadena completa automática:
      1. (Opcional) reset_resultados=true → limpia scores/puntajes antes de sincronizar.
      2. Auto-mapeo si faltan api_fixture_id (detecta liga, matchea equipos y partidos).
      3. Descarga partidos finalizados de API-Football y actualiza la BD.
      4. Avanza el bracket KO (propaga ganadores a la siguiente fase).
      5. Recalcula todos los puntajes y globales A-G.

    Query params:
      force=true            → re-sincroniza incluso partidos ya marcados 'finalizado'.
      max_detalle=N         → máximo de peticiones individuales por run (default 10).
      reset_resultados=true → resetea scores, puntajes y bracket antes de sincronizar.
                              Útil para borrar datos de prueba al iniciar la competencia real.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    # ── Paso 0 (opcional): reset scores/puntajes antes de sincronizar ─────────
    reset_summary: dict = {}
    if reset_resultados:
        if not await _check_superadmin(current):
            raise HTTPException(403, "reset_resultados requiere rol superadmin")
        # a) Reset scores de todos los partidos
        await db.execute(
            text("""
                UPDATE partido
                SET goles_local=NULL, goles_visitante=NULL,
                    minuto_primer_gol=NULL, amarillas=NULL,
                    decisiones_var=NULL, penales_local=NULL, penales_visitante=NULL,
                    estado='programado'
                WHERE torneo_id=:tid
            """),
            {"tid": torneo_id},
        )
        _sopt_r = await db.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='partido' AND table_schema='public'
              AND column_name = ANY(ARRAY['rojas','penales_partido','equipo_clasificado_id'])
        """))
        for _col in {row[0] for row in _sopt_r}:
            await db.execute(text(f"UPDATE partido SET {_col}=NULL WHERE torneo_id=:tid"), {"tid": torneo_id})
        # b) Reset participacion (standings grupos)
        await db.execute(
            text("""UPDATE participacion SET pj=0,pg=0,pe=0,pp=0,gf=0,gc=0,pts=0,clasifica=FALSE
                     WHERE fase_id IN (SELECT id FROM fase WHERE torneo_id=:tid AND tipo='grupo')"""),
            {"tid": torneo_id},
        )
        # c) Reset puntajes calculados
        reset_pts = await _reset_puntajes_todos(db, torneo_id)
        # d) Reset bracket KO a TBD
        try:
            await _resetear_ko_a_tbd(db, torneo_id)
        except Exception as _e:
            log.warning("sync.reset_ko_skip", error=str(_e))
        await db.commit()
        reset_summary = {"reset_resultados": True, **reset_pts}

    from app.services.sync_api_football import sync_torneo

    # ── Paso 1: auto-mapeo + sincronizar resultados con API-Football ──────────
    try:
        sync_summary = await sync_torneo(db, torneo_id, force=force, max_detalle=max_detalle)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Commit resultados antes de recalcular standings y avanzar bracket
    await db.commit()

    actualizados  = sync_summary.get("actualizados", 0)

    # ── Paso 1b: recalcular standings de grupos (PJ/PG/PE/PP/GF/GC/Pts) ────────
    # Siempre se recalcula para que el cuadro refleje el estado actual del torneo.
    try:
        await _recalc_participacion(db, torneo_id)
        await db.commit()
    except Exception as e:
        sync_summary["participacion_error"] = str(e)

    # Siempre avanzar bracket y calcular puntajes en cada sync manual.
    # El costo es bajo y garantiza que el estado sea consistente.

    # ── Paso 2: avanzar bracket KO ───────────────────────────────────────────
    bracket_ok = False
    if True:
        try:
            maps = await ko_scoring.build_num_maps(db, torneo_id)
            await _avanzar_bracket(db, torneo_id, maps)
            await db.commit()
            bracket_ok = True
        except Exception as e:
            sync_summary["bracket_error"] = str(e)

    # ── Paso 3: recalcular puntajes ──────────────────────────────────────────
    puntajes_ok = False
    puntajes_summary: dict = {}
    if True:
        try:
            await _ensure_detalle_table(db)
            r_torneo = await db.execute(
                text("""
                    SELECT COALESCE(c.codigo, '') AS competicion_codigo
                    FROM torneo t
                    LEFT JOIN competicion c ON c.id = t.competicion_id
                    WHERE t.id = :tid
                """),
                {"tid": torneo_id},
            )
            row_torneo = r_torneo.mappings().first()
            competicion_codigo = (row_torneo or {}).get("competicion_codigo") or None
            engine = scoring_registry.get_engine(competicion_codigo)

            calc = ScoringCalculator(db)
            result = await calc.calculate(torneo_id, engine)
            if result:
                global_result = await calc.calculate_global(torneo_id, engine)
                await db.commit()
                puntajes_ok = True
                puntajes_summary = {
                    "plenos":              result["plenos"],
                    "aciertos":            result["aciertos"],
                    "fallos":              result["fallos"],
                    "globales_procesadas": global_result.get("procesadas", 0),
                }
        except Exception as e:
            sync_summary["puntajes_error"] = str(e)

    await _audit_log(
        "sync:resultados", "bets",
        current=current, method="POST",
        path=f"/api/v1/bets/sync-resultados/{torneo_id}",
        resource_id=str(torneo_id),
        details={
            "evento":      "sincronización API-Football",
            "force":       force,
            "reset_resultados": reset_resultados,
            **reset_summary,
            "actualizados": actualizados,
            "api_calls":   sync_summary.get("api_calls", 0),
            "bracket_ok":  bracket_ok,
            "puntajes_ok": puntajes_ok,
        },
    )

    return {
        "ok":          True,
        "actualizados": actualizados,          # top-level para compat con portal JS
        "sync":        sync_summary,
        "bracket_ok":  bracket_ok,
        "puntajes_ok": puntajes_ok,
        "puntajes":    puntajes_summary,
    }


@router.get("/api-mapeo/{torneo_id}", summary="Datos para mapeo API-Football ↔ BD (admin)")
async def api_mapeo_get(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Carga desde API-Football la lista de equipos y fixtures del torneo,
    y los devuelve junto a los registros DB para que el admin realice el mapeo.

    Retorna:
      api_teams:    [{id, name, logo}] — equipos desde API-Football
      api_fixtures: [{id, date, home_id, home_name, away_id, away_name, round, status}]
      db_equipos:   [{id, nombre, api_team_id}]
      db_partidos:  [{id, fecha, equipo_local_id, local_nombre, equipo_visitante_id,
                       visitante_nombre, fase_tipo, api_fixture_id}]
      config:       {api_league_id, api_season} — configuración actual del torneo
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    from app.services.sync_api_football import _headers, API_BASE
    from app.core.config import settings as _settings

    if not _settings.APIFOOTBALL_KEY:
        raise HTTPException(400, "APIFOOTBALL_KEY no configurado en .env")

    # ── Cargar config del torneo ──────────────────────────────────────────────
    r_cfg = await db.execute(
        text("""
            SELECT t.id, t.api_season, c.api_league_id, c.id AS competicion_id
            FROM torneo t
            LEFT JOIN competicion c ON c.id = t.competicion_id
            WHERE t.id = :tid
        """),
        {"tid": torneo_id},
    )
    cfg = r_cfg.mappings().first()
    if not cfg:
        raise HTTPException(404, "Torneo no encontrado")

    api_season    = cfg["api_season"]
    api_league_id = cfg["api_league_id"]

    # ── Cargar equipos DB ─────────────────────────────────────────────────────
    r_eq = await db.execute(
        text("SELECT id, COALESCE(nombre_es, nombre) AS nombre, api_team_id FROM equipo ORDER BY nombre")
    )
    db_equipos = [dict(row) for row in r_eq.mappings()]

    # ── Cargar partidos DB ────────────────────────────────────────────────────
    r_p = await db.execute(
        text("""
            SELECT p.id, p.fecha, p.api_fixture_id, p.equipo_local_id, p.equipo_visitante_id,
                   f.tipo AS fase_tipo, f.nombre AS fase_nombre,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visitante_nombre
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid
            ORDER BY p.fecha, p.id
        """),
        {"tid": torneo_id},
    )
    db_partidos = []
    for row in r_p.mappings():
        d = dict(row)
        if d.get("fecha"):
            d["fecha"] = d["fecha"].isoformat() if hasattr(d["fecha"], "isoformat") else str(d["fecha"])
        db_partidos.append(d)

    # ── Si no hay api_league_id o api_season, devolver solo BD ───────────────
    if not api_season or not api_league_id:
        return {
            "api_teams":    [],
            "api_fixtures": [],
            "db_equipos":   db_equipos,
            "db_partidos":  db_partidos,
            "config":       {"api_league_id": api_league_id, "api_season": api_season},
            "warning":      "Faltan api_league_id o api_season. Configurá primero y volvé a cargar.",
        }

    # ── Fetch API-Football ────────────────────────────────────────────────────
    api_teams:    list[dict] = []
    api_fixtures: list[dict] = []
    api_error: str | None = None

    import httpx
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Equipos del torneo
            r1 = await client.get(
                f"{API_BASE}/teams",
                params={"league": api_league_id, "season": api_season},
                headers=_headers(),
            )
            r1.raise_for_status()
            for t in r1.json().get("response", []):
                api_teams.append({
                    "id":   t["team"]["id"],
                    "name": t["team"]["name"],
                    "logo": t["team"].get("logo", ""),
                })
            api_teams.sort(key=lambda x: x["name"])

            # Fixtures del torneo
            r2 = await client.get(
                f"{API_BASE}/fixtures",
                params={"league": api_league_id, "season": api_season},
                headers=_headers(),
            )
            r2.raise_for_status()
            for fix in r2.json().get("response", []):
                api_fixtures.append({
                    "id":         fix["fixture"]["id"],
                    "date":       fix["fixture"]["date"],
                    "round":      fix["league"].get("round", ""),
                    "status":     fix["fixture"]["status"]["short"],
                    "home_id":    fix["teams"]["home"]["id"],
                    "home_name":  fix["teams"]["home"]["name"],
                    "away_id":    fix["teams"]["away"]["id"],
                    "away_name":  fix["teams"]["away"]["name"],
                })
            api_fixtures.sort(key=lambda x: x["date"])

    except Exception as e:
        api_error = str(e)

    return {
        "api_teams":    api_teams,
        "api_fixtures": api_fixtures,
        "db_equipos":   db_equipos,
        "db_partidos":  db_partidos,
        "config":       {"api_league_id": api_league_id, "api_season": api_season},
        **({"api_error": api_error} if api_error else {}),
    }


class ApiMapeoSave(BaseModel):
    api_league_id: int | None = None
    api_season:    int | None = None
    equipos:  list[dict] = []   # [{id: int, api_team_id: int}]
    partidos: list[dict] = []   # [{id: int, api_fixture_id: int}]


@router.post("/api-mapeo/{torneo_id}/save", summary="Guardar mapeo API-Football → BD (admin)")
async def api_mapeo_save(
    torneo_id: int, body: ApiMapeoSave, current: CurrentUser, db: DBSession
) -> dict:
    """Guarda en BD los IDs de API-Football para liga, season, equipos y partidos."""
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    actualizados_equipos  = 0
    actualizados_partidos = 0

    # ── Liga + Season ─────────────────────────────────────────────────────────
    if body.api_league_id is not None:
        r_comp = await db.execute(
            text("SELECT competicion_id FROM torneo WHERE id = :tid"),
            {"tid": torneo_id},
        )
        row_comp = r_comp.mappings().first()
        if row_comp and row_comp["competicion_id"]:
            await db.execute(
                text("UPDATE competicion SET api_league_id = :lid WHERE id = :cid"),
                {"lid": body.api_league_id, "cid": row_comp["competicion_id"]},
            )

    if body.api_season is not None:
        await db.execute(
            text("UPDATE torneo SET api_season = :s WHERE id = :tid"),
            {"s": body.api_season, "tid": torneo_id},
        )

    # ── Equipos ───────────────────────────────────────────────────────────────
    for eq in body.equipos:
        db_id       = eq.get("id")
        api_team_id = eq.get("api_team_id")
        if db_id and api_team_id is not None:
            await db.execute(
                text("UPDATE equipo SET api_team_id = :atid WHERE id = :eid"),
                {"atid": api_team_id, "eid": db_id},
            )
            actualizados_equipos += 1

    # ── Partidos ──────────────────────────────────────────────────────────────
    for p in body.partidos:
        db_id          = p.get("id")
        api_fixture_id = p.get("api_fixture_id")
        if db_id and api_fixture_id is not None:
            await db.execute(
                text("UPDATE partido SET api_fixture_id = :afid WHERE id = :pid"),
                {"afid": api_fixture_id, "pid": db_id},
            )
            actualizados_partidos += 1

    await db.commit()

    await _audit_log(
        "mapeo:api_football", "bets",
        current=current, method="POST",
        path=f"/api/v1/bets/api-mapeo/{torneo_id}/save",
        resource_id=str(torneo_id),
        details={
            "evento":               "mapeo API-Football guardado",
            "actualizados_equipos":  actualizados_equipos,
            "actualizados_partidos": actualizados_partidos,
        },
    )

    return {
        "ok":                    True,
        "actualizados_equipos":  actualizados_equipos,
        "actualizados_partidos": actualizados_partidos,
    }


@router.post("/api-mapeo/{torneo_id}/auto", summary="Auto-mapear equipos y partidos desde API-Football (admin)")
async def api_mapeo_auto(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Detecta automáticamente y guarda en BD los api_team_id y api_fixture_id
    haciendo match por nombre normalizado y par de equipos.
    También auto-detecta api_league_id y api_season si no están configurados.
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    from app.services.sync_api_football import auto_mapeo_torneo
    from app.core.config import settings as _settings
    import httpx

    if not _settings.APIFOOTBALL_KEY:
        raise HTTPException(400, "APIFOOTBALL_KEY no configurado en .env")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            result = await auto_mapeo_torneo(db, torneo_id, client)
    except Exception as e:
        raise HTTPException(500, f"Error en auto-mapeo: {e}")

    return result


@router.get("/test-verificacion/{torneo_id}", summary="Datos crudos para verificar el scoring (admin, solo pruebas)")
async def test_verificacion(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """Devuelve datos crudos (sin cálculo) para recalcular el puntaje de forma independiente."""
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    r_part = await db.execute(
        text("""
            SELECT p.id, p.goles_local, p.goles_visitante,
                   p.minuto_primer_gol, p.amarillas, p.decisiones_var
            FROM partido p
            JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
            WHERE p.torneo_id = :tid AND p.estado = 'finalizado'
              AND p.goles_local IS NOT NULL AND p.goles_visitante IS NOT NULL
        """),
        {"tid": torneo_id},
    )
    partidos = [dict(row) for row in r_part.mappings()]
    pids = [p["id"] for p in partidos]

    apuestas = []
    if pids:
        r_ap = await db.execute(
            text("""
                SELECT id, apostador_id, partido_id,
                       pred_local, pred_visitante,
                       pred_minuto_gol, pred_amarillas, pred_var,
                       puntos, puntos_bonus
                FROM apuesta WHERE partido_id = ANY(:pids)
            """),
            {"pids": pids},
        )
        apuestas = [dict(row) for row in r_ap.mappings()]

    uids = sorted({a["apostador_id"] for a in apuestas})
    usuarios: dict[int, str] = {}
    if uids:
        async with _app_engine.connect() as conn:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"),
                {"ids": uids},
            )
            usuarios = {row["id"]: row["username"] for row in ur.mappings()}

    # Tabla de posiciones (standings) derivada de los resultados simulados
    standings: dict = {}
    try:
        st = await _calc_standings_reales(db, torneo_id)
        for letra, grupo in st.items():
            standings[letra] = [
                {
                    "pos": e.get("pos"), "equipo_id": e["equipo_id"], "nombre": e["nombre"],
                    "pj": e["pj"], "pg": e["pg"], "pe": e["pe"], "pp": e["pp"],
                    "gf": e["gf"], "gc": e["gc"], "gd": e["gd"], "pts": e["pts"],
                }
                for e in grupo["equipos"]
            ]
    except Exception as e:
        await db.rollback()
        standings = {"error": str(e)}

    return {
        "partidos":  partidos,
        "apuestas":  apuestas,
        "usuarios":  usuarios,
        "standings": standings,
    }


# ── Verificación de integridad de equipos por competición ────────────────────

@router.get("/verificar-equipos/{torneo_id}", summary="Verifica integridad de equipos del torneo (admin)")
async def verificar_equipos(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    """
    Algoritmo de verificación de equipos para un torneo:

    1. COMPETICION_MISMATCH: partidos con equipos de otra competición
    2. EQUIPOS_SIN_COMPETICION: equipos que participan pero no tienen competicion_id asignado
    3. COUNT_CHECK: cantidad de equipos distintos vs num_equipos_esperado de la competición
    4. CROSS_CONTAMINACION: equipos de competición X apareciendo en torneo de competición Y
    5. EQUIPOS_SIN_ISO: selecciones sin codigo_iso (solo aplica si la competición es de selecciones)

    Retorna: { "ok": bool, "errores": [...], "advertencias": [...], "resumen": {...} }
    """
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    errores     = []
    advertencias = []

    # ── Info del torneo y competición ─────────────────────────────────────────
    r_torneo = await db.execute(
        text("""
            SELECT t.id, t.nombre, c.id AS comp_id, c.nombre AS comp_nombre,
                   c.codigo, c.num_equipos_esperado
            FROM torneo t
            JOIN competicion c ON c.id = t.competicion_id
            WHERE t.id = :tid
        """),
        {"tid": torneo_id},
    )
    torneo = r_torneo.mappings().first()
    if not torneo:
        raise HTTPException(404, f"Torneo {torneo_id} no encontrado")

    comp_id         = torneo["comp_id"]
    comp_nombre     = torneo["comp_nombre"]
    num_esperado    = torneo["num_equipos_esperado"]

    # ── 1. Equipos distintos que participan en este torneo ───────────────────
    r_equipos = await db.execute(
        text("""
            SELECT DISTINCT e.id, e.nombre, e.nombre_es, e.competicion_id, e.codigo_iso
            FROM equipo e
            JOIN partido p ON (p.equipo_local_id = e.id OR p.equipo_visitante_id = e.id)
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid
              AND e.id IS NOT NULL
            ORDER BY e.nombre
        """),
        {"tid": torneo_id},
    )
    equipos_en_torneo = list(r_equipos.mappings())
    total_equipos = len(equipos_en_torneo)

    # ── 2. CROSS_CONTAMINACION: equipos de otra competición ──────────────────
    cross = [
        e for e in equipos_en_torneo
        if e["competicion_id"] is not None and e["competicion_id"] != comp_id
    ]
    for e in cross:
        errores.append({
            "tipo":     "CROSS_CONTAMINACION",
            "equipo_id": e["id"],
            "equipo":   e["nombre"],
            "msg":      f"El equipo '{e['nombre']}' (id={e['id']}) pertenece a "
                        f"competicion_id={e['competicion_id']} pero está en torneo "
                        f"de competicion_id={comp_id} ({comp_nombre})",
        })

    # ── 3. EQUIPOS_SIN_COMPETICION: participan pero sin competicion_id ────────
    sin_comp = [e for e in equipos_en_torneo if e["competicion_id"] is None]
    for e in sin_comp:
        advertencias.append({
            "tipo":      "SIN_COMPETICION",
            "equipo_id": e["id"],
            "equipo":    e["nombre"],
            "msg":       f"El equipo '{e['nombre']}' (id={e['id']}) no tiene competicion_id asignado",
        })

    # ── 4. COUNT_CHECK: cantidad vs esperado ─────────────────────────────────
    estado_count = "sin_validacion"
    if num_esperado is not None:
        if total_equipos < num_esperado:
            estado_count = "FALTAN_EQUIPOS"
            errores.append({
                "tipo":     "COUNT_FALTAN",
                "msg":      f"Se esperan {num_esperado} equipos para {comp_nombre}, "
                            f"solo hay {total_equipos} en los partidos del torneo.",
                "esperado": num_esperado,
                "actual":   total_equipos,
                "faltan":   num_esperado - total_equipos,
            })
        elif total_equipos > num_esperado:
            estado_count = "EQUIPOS_DE_MAS"
            errores.append({
                "tipo":     "COUNT_DE_MAS",
                "msg":      f"Se esperan {num_esperado} equipos para {comp_nombre}, "
                            f"hay {total_equipos}. Posible duplicado o equipo incorrecto.",
                "esperado": num_esperado,
                "actual":   total_equipos,
            })
        else:
            estado_count = "OK"

    # ── 5. EQUIPOS_SIN_ISO (solo selecciones nacionales — competicion con código) ─
    es_selecciones = torneo["codigo"] and "copa_mundo" in (torneo["codigo"] or "")
    sin_iso = [
        e for e in equipos_en_torneo
        if e["codigo_iso"] is None and e["competicion_id"] == comp_id
    ]
    if es_selecciones and sin_iso:
        for e in sin_iso:
            advertencias.append({
                "tipo":      "SIN_ISO",
                "equipo_id": e["id"],
                "equipo":    e["nombre"],
                "msg":       f"Selección '{e['nombre']}' sin codigo_iso (necesario para banderas y reportes)",
            })

    # ── 6. Partidos con equipo_local_id o equipo_visitante_id NULL ────────────
    r_null = await db.execute(
        text("""
            SELECT COUNT(*) AS total
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid
              AND (p.equipo_local_id IS NULL OR p.equipo_visitante_id IS NULL)
        """),
        {"tid": torneo_id},
    )
    partidos_sin_equipo = r_null.scalar() or 0
    if partidos_sin_equipo:
        errores.append({
            "tipo":  "PARTIDOS_SIN_EQUIPO",
            "msg":   f"{partidos_sin_equipo} partido(s) sin equipo asignado (equipo_local_id o visitante NULL)",
            "count": partidos_sin_equipo,
        })

    # ── Resumen ───────────────────────────────────────────────────────────────
    ok = len(errores) == 0
    resumen = {
        "torneo_id":         torneo_id,
        "torneo":            torneo["nombre"],
        "competicion":       comp_nombre,
        "competicion_id":    comp_id,
        "competicion_codigo": torneo["codigo"],
        "total_equipos_en_partidos": total_equipos,
        "num_equipos_esperado":      num_esperado,
        "estado_count":      estado_count,
        "cross_contaminacion": len(cross),
        "sin_competicion_id":  len(sin_comp),
        "sin_codigo_iso":      len(sin_iso) if es_selecciones else "N/A",
        "partidos_sin_equipo": partidos_sin_equipo,
        "total_errores":       len(errores),
        "total_advertencias":  len(advertencias),
    }

    return {
        "ok":          ok,
        "errores":     errores,
        "advertencias": advertencias,
        "resumen":     resumen,
        "equipos":     [
            {"id": e["id"], "nombre": e["nombre"], "competicion_id": e["competicion_id"],
             "codigo_iso": e["codigo_iso"]}
            for e in equipos_en_torneo
        ],
    }


# ── Bracket real + simulación secuencial ─────────────────────────────────────

async def _sim_resultado_partido(db, pid: int, es_grupo: bool):
    """Genera un resultado real aleatorio para un partido (con bonus y penales si aplica)."""
    gl = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
    gv = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
    minuto = random.randint(1, 90) if (gl + gv) > 0 else None
    amarillas = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 12, 22, 26, 18, 11, 6])[0]
    var = random.choices([0, 1], weights=[65, 35])[0]
    pen_l = pen_v = None
    if not es_grupo and gl == gv:
        pen_l, pen_v = random.choice([(4, 2), (5, 4), (3, 1), (5, 3), (4, 5), (2, 4), (1, 3)])
    await db.execute(
        text("""
            UPDATE partido
            SET goles_local=:gl, goles_visitante=:gv,
                minuto_primer_gol=:m, amarillas=:a, rojas=:rojas, decisiones_var=:v,
                penales_local=:pl, penales_visitante=:pv, estado='finalizado'
            WHERE id=:pid
        """),
        {"gl": gl, "gv": gv, "m": minuto, "a": amarillas, "rojas": random.choices([0,1,2], weights=[78,18,4])[0], "v": var,
         "pl": pen_l, "pv": pen_v, "pid": pid},
    )


async def _generar_pred_apostador(db, uid: int, pid: int):
    """Inserta/actualiza una predicción aleatoria (marcador + bonus) de un apostador."""
    pl = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
    pv = random.choices([0, 1, 2, 3], weights=[18, 38, 30, 14])[0]
    pmg = random.randint(1, 90)
    pam = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[5, 12, 22, 26, 18, 11, 6])[0]
    pvar = random.choices([0, 1], weights=[60, 40])[0]
    projas = random.choices([0, 1, 2], weights=[78, 18, 4])[0]
    ppp = random.choices([0, 1, 2], weights=[70, 22, 8])[0]
    await db.execute(
        text("""
            INSERT INTO apuesta
                (apostador_id, partido_id, pred_local, pred_visitante,
                 pred_minuto_gol, pred_amarillas, pred_var,
                 pred_rojas, pred_penales_partido)
            VALUES (:uid, :pid, :pl, :pv, :pmg, :pam, :pvar, :projas, :ppp)
            ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                pred_local=EXCLUDED.pred_local, pred_visitante=EXCLUDED.pred_visitante,
                pred_minuto_gol=EXCLUDED.pred_minuto_gol,
                pred_amarillas=EXCLUDED.pred_amarillas, pred_var=EXCLUDED.pred_var,
                pred_rojas=EXCLUDED.pred_rojas,
                pred_penales_partido=EXCLUDED.pred_penales_partido,
                updated_at=NOW()
        """),
        {"uid": uid, "pid": pid, "pl": pl, "pv": pv, "pmg": pmg, "pam": pam, "pvar": pvar,
         "projas": projas, "ppp": ppp},
    )


async def _grupos_completos(db, torneo_id: int) -> bool:
    """True si TODOS los partidos de fase de grupos están finalizados (al menos 1 existe)."""
    r = await db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE p.estado != 'finalizado') AS pendientes,
                COUNT(*) AS total
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND f.tipo = 'grupo'
        """),
        {"tid": torneo_id},
    )
    row = r.mappings().first()
    if not row or not row["total"]:
        return False
    return row["pendientes"] == 0


async def _resetear_ko_a_tbd(db, torneo_id: int) -> None:
    """
    Resetea TODOS los partidos KO a TBD (equipo placeholder) y limpia resultados.
    Se llama cuando la fase de grupos no está completa para asegurar que el
    bracket no muestre equipos de corridas anteriores (ej: test_integral).
    """
    tbd = await ko_scoring._tbd_id(db)
    if tbd is None:
        return  # Sin equipo TBD en BD, no hacer nada

    # Todos los partidos KO de este torneo
    r = await db.execute(
        text("""
            SELECT p.id, p.equipo_local_id, p.equipo_visitante_id
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND f.tipo != 'grupo'
        """),
        {"tid": torneo_id},
    )
    partidos_ko = list(r.mappings())

    for p in partidos_ko:
        # Solo resetear si tiene equipos reales (no TBD ya)
        if p["equipo_local_id"] != tbd or p["equipo_visitante_id"] != tbd:
            await db.execute(
                text("""
                    UPDATE partido
                    SET equipo_local_id    = :tbd,
                        equipo_visitante_id = :tbd,
                        estado              = 'programado',
                        goles_local         = NULL,
                        goles_visitante     = NULL,
                        goles_local_prorroga  = NULL,
                        goles_visitante_prorroga = NULL,
                        penales_local       = NULL,
                        penales_visitante   = NULL,
                        minuto_primer_gol   = NULL,
                        amarillas           = NULL,
                        decisiones_var      = NULL,
                        equipo_clasificado_id = NULL
                    WHERE id = :pid
                """),
                {"tbd": tbd, "pid": p["id"]},
            )
            # Limpiar puntajes de apuestas de este partido
            await db.execute(
                text("UPDATE apuesta SET puntos = 0, puntos_bonus = 0 WHERE partido_id = :pid"),
                {"pid": p["id"]},
            )


async def _avanzar_bracket(db, torneo_id: int, maps: dict, hasta_tipo: str | None = None):
    """Avanza el bracket real asignando equipos a las fases KO según resultados.

    - Si grupos NO están completos: resetea TODOS los partidos KO a TBD.
    - Si grupos SÍ están completos: arma R32 desde standings y propaga KO.
    - Si hasta_tipo se indica, sólo avanza hasta esa fase (inclusive).
    """
    orden_tipos = ["ronda32", "ronda16", "cuartos", "semis", "tercer_puesto", "final"]

    if not await _grupos_completos(db, torneo_id):
        # Grupos incompletos → limpiar todo el bracket KO a TBD
        await _resetear_ko_a_tbd(db, torneo_id)
        return

    # Grupos completos → armar R32 desde standings reales
    standings = await _calc_standings_reales(db, torneo_id)
    if standings:
        mejores, _ = seleccionar_mejores_terceros(standings)
        await ko_scoring.avanzar_ronda32(db, torneo_id, maps["num2pid"], standings, mejores)

    if hasta_tipo == "ronda32":
        return
    for tipo in orden_tipos[1:]:
        await ko_scoring.avanzar_fase_ko(db, torneo_id, tipo, maps)
        if hasta_tipo == tipo:
            break


@router.post("/avanzar-bracket/{torneo_id}", summary="Avanzar el bracket real desde resultados (admin)")
async def avanzar_bracket(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    maps = await ko_scoring.build_num_maps(db, torneo_id)
    await _avanzar_bracket(db, torneo_id, maps)
    await db.commit()
    await _audit_log("avance:bracket", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/avanzar-bracket/{torneo_id}",
                     resource_id=str(torneo_id),
                     details={"evento": "avance manual del bracket desde resultados"})
    return {"ok": True, "mensaje": "Bracket real actualizado desde resultados"}


@router.post("/simular-secuencial/{torneo_id}/{fase_id}",
             summary="Simular secuencialmente hasta la fase objetivo: avanza bracket, genera pronósticos y resultados, y puntúa (admin)")
async def simular_secuencial(torneo_id: int, fase_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    # Fases del torneo ordenadas
    rf = await db.execute(
        text("""SELECT id, nombre, tipo, orden FROM fase
                WHERE torneo_id=:tid ORDER BY orden, nombre"""),
        {"tid": torneo_id},
    )
    fases = [dict(r) for r in rf.mappings()]
    objetivo = next((f for f in fases if f["id"] == fase_id), None)
    if not objetivo:
        raise HTTPException(404, "Fase objetivo no encontrada")
    target_orden = objetivo["orden"]

    # Apostadores del torneo (los que ya tienen apuestas de grupo)
    ra = await db.execute(
        text("""SELECT DISTINCT a.apostador_id
                FROM apuesta a JOIN partido p ON p.id=a.partido_id
                JOIN fase f ON f.id=p.fase_id
                WHERE f.torneo_id=:tid AND f.tipo='grupo'"""),
        {"tid": torneo_id},
    )
    apostadores = [row[0] for row in ra]
    if not apostadores:
        raise HTTPException(400, "No hay apostadores con pronósticos de grupo")

    maps = await ko_scoring.build_num_maps(db, torneo_id)
    pasos: list[dict] = []

    for f in fases:
        if f["orden"] > target_orden:
            break
        tipo = f["tipo"]
        es_grupo = tipo == "grupo"

        # 1) Avanzar bracket (asignar equipos) para fases KO antes de pronosticar
        if not es_grupo:
            await _avanzar_bracket(db, torneo_id, maps, hasta_tipo=tipo)

        # partidos de la fase
        rp = await db.execute(text("SELECT id FROM partido WHERE fase_id=:fid ORDER BY id"),
                              {"fid": f["id"]})
        pids = [row[0] for row in rp]

        # 2) Generar pronósticos KO de cada apostador (los de grupo ya existen)
        preds_creadas = 0
        if not es_grupo:
            for pid in pids:
                for uid in apostadores:
                    await _generar_pred_apostador(db, uid, pid)
                    preds_creadas += 1

        # 3) Simular resultados reales de la fase
        for pid in pids:
            await _sim_resultado_partido(db, pid, es_grupo)

        await db.commit()  # confirmar para que la próxima fase vea resultados
        pasos.append({"fase": f["nombre"], "tipo": tipo,
                      "partidos": len(pids), "pred_generadas": preds_creadas})

    # 4) Avanzar bracket completo final y puntuar todo
    await _avanzar_bracket(db, torneo_id, maps, hasta_tipo=objetivo["tipo"])
    await _recalc_participacion(db, torneo_id)
    await db.commit()
    resumen = await calcular_puntajes(torneo_id, current, db)

    await _audit_log("simulacion:secuencial", "bets", current=current, method="POST",
                     path=f"/api/v1/bets/simular-secuencial/{torneo_id}/{fase_id}",
                     resource_id=str(torneo_id),
                     details={"evento": "simulación secuencial (paso de fase a fase)",
                              "objetivo": objetivo["nombre"],
                              "pasos": pasos, "apostadores": len(apostadores)})
    return {"ok": True, "objetivo": objetivo["nombre"], "pasos": pasos, "puntajes": resumen}


# ── Puntos por fase (análisis) ───────────────────────────────────────────────

async def _puntos_por_fase_data(db, torneo_id: int) -> dict:
    """Lee puntaje_detalle y arma: por_apostador_fase y totales por fase."""
    try:
        r = await db.execute(
            text("""
                SELECT d.apostador_id, d.fase_id, d.fase_tipo, d.fase_nombre,
                       SUM(d.pts_marcador)::int AS marcador,
                       SUM(d.pts_minuto)::int   AS minuto,
                       SUM(d.pts_amarillas)::int AS amarillas,
                       SUM(d.pts_var)::int      AS var,
                       SUM(d.pts_bonus)::int    AS bonus,
                       SUM(d.pts_total)::int    AS total,
                       COUNT(*)::int            AS partidos
                FROM puntaje_detalle d
                WHERE d.torneo_id=:tid
                GROUP BY d.apostador_id, d.fase_id, d.fase_tipo, d.fase_nombre
                ORDER BY d.apostador_id
            """),
            {"tid": torneo_id},
        )
    except Exception:
        await db.rollback()
        return {"filas": [], "usuarios": {}}
    filas = [dict(row) for row in r.mappings()]
    uids = sorted({f["apostador_id"] for f in filas})
    usuarios: dict[int, str] = {}
    if uids:
        async with _app_engine.connect() as conn:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"), {"ids": uids})
            usuarios = {row["id"]: row["username"] for row in ur.mappings()}
    for f in filas:
        f["nombre"] = usuarios.get(f["apostador_id"], f"Usuario {f['apostador_id']}")
    return {"filas": filas, "usuarios": usuarios}


@router.get("/puntos-por-fase/{torneo_id}", summary="Puntos por fase de cada apostador (análisis)")
async def puntos_por_fase(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    data = await _puntos_por_fase_data(db, torneo_id)
    return {"torneo_id": torneo_id, "filas": data["filas"]}


@router.get("/puntos-por-fase/{torneo_id}/excel", summary="Exportar puntos por fase a Excel (admin)")
async def puntos_por_fase_excel(torneo_id: int, current: CurrentUser, db: DBSession):
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")
    try:
        wb, _ = await _build_auditoria_workbook(db, torneo_id)
    except ImportError:
        raise HTTPException(500, "openpyxl no está instalado")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "static", "exports")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    fname = f"puntos_por_fase_torneo_{torneo_id}.xlsx"
    fpath = os.path.join(out_dir, fname)
    wb.save(fpath)
    return FileResponse(fpath, filename=fname,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── Auditoría por fase (real vs apostado, puntos por ítem) ───────────────────

@router.get("/auditoria-fase/{torneo_id}", summary="Auditoría por fase: real vs apostado y puntos por ítem")
async def auditoria_fase(torneo_id: int, current: CurrentUser, db: DBSession,
                         apostador_id: int | None = None) -> dict:
    """Devuelve, por fase y por partido, el resultado real vs el apostado y los
    puntos ganados por ítem (marcador/minuto/amarillas/VAR). Si se pasa
    apostador_id, filtra por ese apostador."""
    if not await _check_admin(current):
        # Un apostador puede ver SU propia auditoría
        apostador_id = current.id

    params: dict = {"tid": torneo_id}
    filtro = ""
    if apostador_id is not None:
        filtro = " AND d.apostador_id = :uid"
        params["uid"] = apostador_id

    try:
        r = await db.execute(
            text(f"""
                SELECT d.fase_id, d.fase_tipo, d.fase_nombre, d.partido_id, d.apostador_id,
                       d.multiplicador, d.pred_local, d.pred_visitante,
                       d.real_local, d.real_visitante, d.pts_marcador,
                       d.pred_minuto, d.real_minuto, d.gano_minuto, d.pts_minuto,
                       d.pred_amarillas, d.real_amarillas, d.pts_amarillas,
                       d.pred_var, d.real_var, d.pts_var, d.pts_bonus, d.pts_total
                FROM puntaje_detalle d
                WHERE d.torneo_id=:tid {filtro}
                ORDER BY d.fase_id, d.partido_id, d.apostador_id
            """),
            params,
        )
    except Exception:
        await db.rollback()
        return {"torneo_id": torneo_id, "fases": []}

    rows = [dict(row) for row in r.mappings()]
    uids = sorted({x["apostador_id"] for x in rows})
    usuarios: dict[int, str] = {}
    if uids:
        async with _app_engine.connect() as conn:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"), {"ids": uids})
            usuarios = {row["id"]: row["username"] for row in ur.mappings()}

    fases: dict[int, dict] = {}
    for x in rows:
        fid = x["fase_id"]
        fase = fases.setdefault(fid, {
            "fase_id": fid, "fase_tipo": x["fase_tipo"],
            "fase_nombre": x["fase_nombre"], "multiplicador": x["multiplicador"],
            "partidos": [],
        })
        fase["partidos"].append({
            "partido_id": x["partido_id"],
            "apostador_id": x["apostador_id"],
            "apostador": usuarios.get(x["apostador_id"], f"Usuario {x['apostador_id']}"),
            "marcador": {"apostado": f"{x['pred_local']}-{x['pred_visitante']}",
                         "real": f"{x['real_local']}-{x['real_visitante']}",
                         "pts": x["pts_marcador"]},
            "minuto": {"apostado": x["pred_minuto"], "real": x["real_minuto"],
                       "gano": x["gano_minuto"], "pts": x["pts_minuto"]},
            "amarillas": {"apostado": x["pred_amarillas"], "real": x["real_amarillas"],
                          "pts": x["pts_amarillas"]},
            "var": {"apostado": x["pred_var"], "real": x["real_var"], "pts": x["pts_var"]},
            "bonus": x["pts_bonus"], "total": x["pts_total"],
        })
    return {"torneo_id": torneo_id, "fases": list(fases.values())}


# ── Transparencia por fase (vista de apostador) ──────────────────────────────

_PHASE_ORDER = ["grupo", "ronda32", "ronda16", "cuartos", "semis", "tercer_puesto", "final"]
_PHASE_LABELS = {
    "grupo": "Grupos", "ronda32": "Ronda 32", "ronda16": "Octavos",
    "cuartos": "Cuartos", "semis": "Semis", "tercer_puesto": "3er puesto", "final": "Final",
}
# Etiquetas completas para títulos de tarjeta (sección "Apuestas y puntajes por fase")
_PHASE_LABELS_FULL = {
    "grupo": "Fase de grupos", "ronda32": "Ronda de 32", "ronda16": "Octavos de final",
    "cuartos": "Cuartos de final", "semis": "Semifinales",
    "tercer_puesto": "Tercer puesto", "final": "Final",
}


async def _build_auditoria_workbook(db, torneo_id: int):
    """Construye el Workbook ÚNICO de auditoría usado por TODAS las salidas de
    export (Auditoría, Transparencia, Puntos por fase).

    Estructura:
      - Hoja 1 'Puntaje general': lista de apostadores con la sumatoria de sus
        puntajes a la fecha (marcador + bonus partido + bonus de terceros),
        rankeada de mayor a menor.
      - Una hoja por fase, empezando por 'Fase de grupos'. Dentro, ordenado por
        grupo y por partido; en cada partido los apostadores se agrupan en
        Pleno (marcador exacto) / Ganador (acertó resultado) / Cero acierto.
        A nivel de apostador se muestra el puntaje del partido (marcador + bonus
        por ítem) sumarizando el Total.

    Devuelve (Workbook, torneo_nombre).
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    tr = await db.execute(text("SELECT nombre FROM torneo WHERE id=:tid"), {"tid": torneo_id})
    t = tr.one_or_none()
    torneo_nombre = t[0] if t else f"Torneo {torneo_id}"

    # Orden jerárquico del bracket (izquierda→derecha) por número de partido FIFA.
    # MISMO orden visual que pronosticos/resultado (_renderBracketTree).
    KO_BRACKET_ORDER = {
        "ronda32":       [74, 77, 73, 75, 83, 84, 81, 82, 76, 78, 79, 80, 86, 88, 85, 87],
        "ronda16":       [89, 90, 93, 94, 91, 92, 95, 96],
        "cuartos":       [97, 98, 99, 100],
        "semis":         [101, 102],
        "tercer_puesto": [103],
        "final":         [104],
    }
    try:
        from app.services.ko_scoring import build_num_maps
        _maps = await build_num_maps(db, torneo_id)
        _pid2num = _maps.get("pid2num", {})
    except Exception:
        _pid2num = {}

    def _bracket_pos(tipo, pid):
        order = KO_BRACKET_ORDER.get(tipo)
        if not order:
            return None
        num = _pid2num.get(pid)
        try:
            return order.index(num)
        except (ValueError, TypeError):
            return None

    rm = await db.execute(
        text("""
            SELECT pd.apostador_id, pd.fase_id, pd.fase_tipo, pd.fase_nombre,
                   pd.partido_id, pd.multiplicador,
                   pd.pred_local, pd.pred_visitante, pd.real_local, pd.real_visitante,
                   pd.pts_marcador_base, pd.pts_marcador,
                   pd.pts_minuto, pd.pts_amarillas, pd.pts_var,
                   COALESCE(pd.pts_rojas, 0)         AS pts_rojas,
                   COALESCE(pd.pts_penales_tanda, 0) AS pts_penales_tanda,
                   pd.pts_bonus, pd.pts_total,
                   p.jornada,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre
            FROM puntaje_detalle pd
            LEFT JOIN partido p ON p.id = pd.partido_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE pd.torneo_id = :tid
            ORDER BY pd.fase_id, p.jornada NULLS LAST, pd.partido_id, pd.apostador_id
        """),
        {"tid": torneo_id},
    )
    detalle = [dict(row) for row in rm.mappings()]

    # Nombres de TODOS los apostadores activos (aunque tengan 0 puntos)
    ids_detalle = {d["apostador_id"] for d in detalle}
    async with _app_engine.connect() as conn:
        ar = await conn.execute(text("""
            SELECT u.id, u.username FROM users u
            JOIN user_roles ur ON ur.user_id = u.id
            JOIN roles ro ON ro.id = ur.role_id
            WHERE ro.name = 'apostador' AND u.is_active = TRUE"""))
        user_map = {row["id"]: row["username"] for row in ar.mappings()}
        extra = [i for i in ids_detalle if i not in user_map]
        if extra:
            ur = await conn.execute(text("SELECT id, username FROM users WHERE id = ANY(:ids)"), {"ids": extra})
            for row in ur.mappings():
                user_map[row["id"]] = row["username"]

    # Puntajes globales A-G por apostador
    pg_r = await db.execute(
        text("SELECT * FROM puntaje_global WHERE torneo_id = :tid"),
        {"tid": torneo_id},
    )
    pts_glob_map: dict = {}
    for row in pg_r.mappings():
        pts_glob_map[row["apostador_id"]] = dict(row)

    # Apuestas globales A-G por apostador (para hoja Globales)
    ag_r = await db.execute(
        text("SELECT * FROM apuesta_global WHERE torneo_id = :tid"),
        {"tid": torneo_id},
    )
    apuesta_glob_map: dict = {}
    for row in ag_r.mappings():
        apuesta_glob_map[row["apostador_id"]] = dict(row)

    # ── Estilos ──
    HDR_FILL    = PatternFill("solid", start_color="1a3a5c")
    GRP_FILL    = PatternFill("solid", start_color="243044")
    ALT_FILL    = PatternFill("solid", start_color="1e2535")
    PART_FILL   = PatternFill("solid", start_color="0f2336")
    GRPHDR_FILL = PatternFill("solid", start_color="33240f")
    PLENO_FILL  = PatternFill("solid", start_color="1e4d2b")
    GANA_FILL   = PatternFill("solid", start_color="3a3410")
    CERO_FILL   = PatternFill("solid", start_color="3a1414")
    TOP_FILL    = PatternFill("solid", start_color="1e4d2b")
    W_FONT     = Font(name="Calibri", color="FFFFFF", bold=True, size=10)
    N_FONT     = Font(name="Calibri", color="E0E0E0", size=9)
    PLENO_FONT = Font(name="Calibri", color="46d17f", bold=True, size=9)
    GANA_FONT  = Font(name="Calibri", color="fbbf24", bold=True, size=9)
    CERO_FONT  = Font(name="Calibri", color="fc7c7c", bold=True, size=9)
    CENTER = Alignment(horizontal="center", vertical="center")
    LEFT   = Alignment(horizontal="left",   vertical="center")
    thin   = Side(style="thin", color="2e3540")
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = Workbook()
    wb.remove(wb.active)

    # ── Hoja 1: Puntaje general ──
    sub: dict[int, dict] = defaultdict(lambda: {"marc": 0, "bonus": 0})
    for d in detalle:
        s = sub[d["apostador_id"]]
        s["marc"]  += (d["pts_marcador"] or 0)
        s["bonus"] += (d["pts_bonus"] or 0)
    gen_cols = ["#", "Apostador", "Marcador", "Bonus partido", "Globales", "Total"]
    gen_w    = [4, 26, 11, 14, 10, 9]
    ws_g = wb.create_sheet("Puntaje general")
    ws_g.sheet_view.showGridLines = False
    for i, w in enumerate(gen_w, start=1):
        ws_g.column_dimensions[chr(64 + i)].width = w
    ws_g.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(gen_cols))
    ws_g.cell(1, 1, f"Puntaje general — {torneo_nombre}").font = Font(
        name="Calibri", color="E05020", bold=True, size=13)
    ws_g["A2"] = f"Generado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}"
    ws_g["A2"].font = Font(name="Calibri", color="888888", size=9)
    for col, h in enumerate(gen_cols, start=1):
        c = ws_g.cell(4, col, h)
        c.font = W_FONT; c.fill = HDR_FILL; c.alignment = CENTER; c.border = BORDER
    filas = []
    for uid, nombre in user_map.items():
        s = sub.get(uid, {"marc": 0, "bonus": 0})
        pg = pts_glob_map.get(uid, {})
        globales = pg.get("pts_total") or 0
        total = s["marc"] + s["bonus"] + globales
        filas.append((nombre, s["marc"], s["bonus"], globales, total))
    filas.sort(key=lambda x: (-x[4], x[0].lower()))
    for idx, f in enumerate(filas, start=1):
        ri = idx + 4
        vals = [idx, f[0], f[1], f[2], f[3], f[4]]
        fill = TOP_FILL if idx == 1 and f[4] > 0 else (ALT_FILL if ri % 2 == 0 else GRP_FILL)
        for col, val in enumerate(vals, start=1):
            c = ws_g.cell(ri, col, val)
            c.font = N_FONT; c.fill = fill; c.border = BORDER
            c.alignment = LEFT if col == 2 else CENTER

    # ── Hojas por fase ──
    # por_fase[fase_tipo][grupo/fase_nombre][partido_id] -> filas de apostadores
    por_fase: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for d in detalle:
        por_fase[d["fase_tipo"]][d["fase_nombre"]][d["partido_id"]].append(d)
    fases = [ft for ft in _PHASE_ORDER if ft in por_fase] + \
            [ft for ft in por_fase if ft not in _PHASE_ORDER]

    cols   = ["Apostador", "Pronóstico", "Marcador", "Min", "Amar", "VAR", "Rojas", "P.Tanda", "Bonus", "Total"]
    cols_w = [26, 11, 10, 6, 6, 6, 6, 7, 8, 8]
    cat_meta = {
        3: ("✅ PLENO — marcador exacto",   PLENO_FILL, PLENO_FONT),
        1: ("➕ GANADOR — acertó resultado", GANA_FILL,  GANA_FONT),
        0: ("✗ CERO ACIERTO",               CERO_FILL,  CERO_FONT),
    }

    for ft in fases:
        nombre_fase = _PHASE_LABELS_FULL.get(ft, ft)
        ws = wb.create_sheet(nombre_fase[:31])
        ws.sheet_view.showGridLines = False
        for i, w in enumerate(cols_w, start=1):
            ws.column_dimensions[chr(64 + i)].width = w
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(cols))
        ws.cell(1, 1, f"{nombre_fase} — {torneo_nombre}").font = Font(
            name="Calibri", color="E05020", bold=True, size=13)
        ri = 3
        es_grupo = ft == "grupo"
        for grupo_nombre in sorted(por_fase[ft].keys()):
            partidos = por_fase[ft][grupo_nombre]
            if es_grupo:
                ws.merge_cells(start_row=ri, start_column=1, end_row=ri, end_column=len(cols))
                c = ws.cell(ri, 1, f"▣ {grupo_nombre}")
                c.font = Font(name="Calibri", color="FFD27F", bold=True, size=12)
                c.fill = GRPHDR_FILL; c.alignment = LEFT
                ri += 2

            def _pkey(pid):
                if not es_grupo:
                    bp = _bracket_pos(ft, pid)
                    if bp is not None:
                        return (0, bp)
                r0 = partidos[pid][0]
                return (r0.get("jornada") or 0, pid)

            for pid in sorted(partidos.keys(), key=_pkey):
                rows = partidos[pid]
                d0 = rows[0]
                partido = f"{d0.get('local_nombre') or '?'} vs {d0.get('visit_nombre') or '?'}"
                real = (f"{d0['real_local']}-{d0['real_visitante']}"
                        if d0["real_local"] is not None else "—")
                jor = f"J{d0['jornada']} · " if d0.get("jornada") else ""
                ws.merge_cells(start_row=ri, start_column=1, end_row=ri, end_column=len(cols))
                mult = d0['multiplicador'] or 1
                py_marker = "   🇵🇾 PARAGUAY x2" if mult > 1 else ""
                c = ws.cell(ri, 1, f"⚽ {jor}{partido}   ·   Real: {real}   ·   x{mult}{py_marker}")
                c.font = Font(name="Calibri", color="FFD27F" if mult == 1 else "7EE0A0", bold=True, size=11)
                c.fill = PART_FILL; c.alignment = LEFT
                ri += 1
                for col, h in enumerate(cols, start=1):
                    c = ws.cell(ri, col, h)
                    c.font = W_FONT; c.fill = HDR_FILL; c.alignment = CENTER; c.border = BORDER
                ri += 1

                buckets = {3: [], 1: [], 0: []}
                for d in rows:
                    base = d["pts_marcador_base"]
                    buckets[3 if base == 3 else (1 if base == 1 else 0)].append(d)

                for cat in (3, 1, 0):
                    grp = buckets[cat]
                    if not grp:
                        continue
                    label, cfill, cfont = cat_meta[cat]
                    ws.merge_cells(start_row=ri, start_column=1, end_row=ri, end_column=len(cols))
                    c = ws.cell(ri, 1, f"{label}   ({len(grp)})")
                    c.font = cfont; c.fill = cfill; c.alignment = LEFT; c.border = BORDER
                    ri += 1
                    grp.sort(key=lambda d: (-(d["pts_total"] or 0),
                                            user_map.get(d["apostador_id"], "").lower()))
                    for d in grp:
                        nombre = user_map.get(d["apostador_id"], f"Usuario {d['apostador_id']}")
                        pred = (f"{d['pred_local']}-{d['pred_visitante']}"
                                if d["pred_local"] is not None else "—")
                        vals = [nombre, pred, d["pts_marcador"], d.get("pts_minuto"),
                                d.get("pts_amarillas"), d.get("pts_var"),
                                d.get("pts_rojas") or None, d.get("pts_penales_tanda") or None,
                                d["pts_bonus"], d["pts_total"]]
                        fill = ALT_FILL if ri % 2 == 0 else GRP_FILL
                        for col, val in enumerate(vals, start=1):
                            c = ws.cell(ri, col, val if val is not None else "")
                            c.font = N_FONT; c.fill = fill; c.border = BORDER
                            c.alignment = LEFT if col == 1 else CENTER
                        ri += 1
                ri += 1  # separador entre partidos

    # ── Hoja Globales A-G ──
    GLOB_FILL   = PatternFill("solid", start_color="1a2840")
    GLOB_HDR    = PatternFill("solid", start_color="1e3a5c")
    GLOB_PT_FNT = Font(name="Calibri", color="46d17f", bold=True, size=9)
    glob_cols   = ["Apostador",
                   "A · Campeón", "B · Fin.1", "B · Fin.2", "C · Goleador",
                   "D · Peor eq.", "E · Gol.G", "E · Gol.P",
                   "F · Etapa Py", "G · Goles Py",
                   "Pts A", "Pts B", "Pts C", "Pts D", "Pts E", "Pts F", "Pts G", "Total"]
    glob_w      = [22, 14, 14, 14, 16, 14, 7, 7, 13, 10, 6, 6, 6, 6, 6, 6, 6, 7]
    ws_gl = wb.create_sheet("Globales")
    ws_gl.sheet_view.showGridLines = False
    for i, w in enumerate(glob_w, start=1):
        ws_gl.column_dimensions[chr(64 + i)].width = w
    ws_gl.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(glob_cols))
    ws_gl.cell(1, 1, f"Pronósticos Globales A-G — {torneo_nombre}").font = Font(
        name="Calibri", color="818cf8", bold=True, size=13)
    ws_gl["A2"] = f"Generado: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}"
    ws_gl["A2"].font = Font(name="Calibri", color="888888", size=9)
    for col, h in enumerate(glob_cols, start=1):
        c = ws_gl.cell(4, col, h)
        c.font = W_FONT; c.fill = GLOB_HDR; c.alignment = CENTER; c.border = BORDER

    # Mapeo equipo_id -> nombre (para los selectores)
    eq_r = await db.execute(
        text("SELECT id, COALESCE(nombre_es, nombre) AS nombre FROM equipo ORDER BY nombre"),
        {},
    )
    eq_map = {row["id"]: row["nombre"] for row in eq_r.mappings()}

    glob_filas = []
    for uid, nombre in user_map.items():
        ag = apuesta_glob_map.get(uid, {})
        pg = pts_glob_map.get(uid, {})
        if not ag and not pg:
            continue
        def _eq(eid): return eq_map.get(eid, f"#{eid}") if eid else "—"
        def _pt(k): v = pg.get(k); return v if v else ""
        row_vals = [
            nombre,
            _eq(ag.get("pred_campeon_id")),
            _eq(ag.get("pred_finalista1_id")),
            _eq(ag.get("pred_finalista2_id")),
            ag.get("pred_goleador") or "—",
            _eq(ag.get("pred_peor_equipo_id")),
            ag.get("pred_goleada_ganador") if ag.get("pred_goleada_ganador") is not None else "—",
            ag.get("pred_goleada_perdedor") if ag.get("pred_goleada_perdedor") is not None else "—",
            ag.get("pred_etapa_paraguay") or "—",
            ag.get("pred_goles_paraguay") if ag.get("pred_goles_paraguay") is not None else "—",
            _pt("pts_campeon"), _pt("pts_finalistas"), _pt("pts_goleador"), _pt("pts_peor_equipo"),
            _pt("pts_goleada"), _pt("pts_etapa_paraguay"), _pt("pts_goles_paraguay"),
            pg.get("pts_total") or "",
        ]
        glob_filas.append((pg.get("pts_total") or 0, nombre, row_vals))

    glob_filas.sort(key=lambda x: (-x[0], x[1].lower()))
    for idx, (_, _, row_vals) in enumerate(glob_filas, start=1):
        ri = idx + 4
        fill = ALT_FILL if ri % 2 == 0 else GLOB_FILL
        for col, val in enumerate(row_vals, start=1):
            c = ws_gl.cell(ri, col, val)
            is_pts_col = col >= len(glob_cols) - 7  # últimas 8 = pts cols
            c.font = GLOB_PT_FNT if (is_pts_col and val) else N_FONT
            c.fill = fill; c.border = BORDER
            c.alignment = LEFT if col == 1 else CENTER

    if not glob_filas:
        ws_gl.merge_cells(start_row=5, start_column=1, end_row=5, end_column=len(glob_cols))
        c = ws_gl.cell(5, 1, "Sin pronósticos globales registrados")
        c.font = N_FONT; c.fill = GLOB_FILL; c.alignment = CENTER

    if not wb.sheetnames:
        wb.create_sheet("Sin datos")
    return wb, torneo_nombre


@router.get("/transparencia/{torneo_id}",
            summary="Vista de transparencia por fase: resultados/clasificados reales, mis apuestas+puntajes y ranking acumulado con subtotal")
async def transparencia(torneo_id: int, current: CurrentUser, db: DBSession,
                        apostador_id: int | None = None) -> dict:
    # Nombres de equipos
    re_ = await db.execute(text("SELECT id, COALESCE(nombre_es, nombre) AS n FROM equipo"))
    equipos = {row[0]: row[1] for row in re_}

    # 1) Clasificados reales — fase de grupos
    grupos_out: list[dict] = []
    try:
        st = await _calc_standings_reales(db, torneo_id)
        if st:
            mejores, _ = seleccionar_mejores_terceros(st)
            terceros_ids = {t["equipo_id"] for t in mejores}
            for letra in sorted(st.keys()):
                eqs = st[letra]["equipos"]
                grupos_out.append({"grupo": letra, "equipos": [
                    {"nombre": e["nombre"], "pos": e.get("pos"), "pj": e["pj"],
                     "pts": e["pts"], "gd": e["gd"], "gf": e["gf"],
                     "clasificado": (e.get("pos") in (1, 2)) or (e["equipo_id"] in terceros_ids),
                     "tercero": e["equipo_id"] in terceros_ids}
                    for e in eqs]})
    except Exception:
        await db.rollback()

    # 2) Resultados reales — fases KO (con ganador que avanza)
    rk = await db.execute(
        text("""
            SELECT f.id AS fase_id, f.tipo, f.nombre, f.orden,
                   p.id AS pid, p.equipo_local_id, p.equipo_visitante_id,
                   p.goles_local, p.goles_visitante,
                   p.penales_local, p.penales_visitante, p.estado
            FROM fase f JOIN partido p ON p.fase_id = f.id
            WHERE f.torneo_id = :tid AND f.tipo <> 'grupo'
            ORDER BY f.orden, p.id
        """),
        {"tid": torneo_id},
    )
    ko_map: dict[int, dict] = {}
    for row in rk.mappings():
        d = dict(row)
        fase = ko_map.setdefault(d["fase_id"], {
            "fase_id": d["fase_id"], "tipo": d["tipo"], "nombre": d["nombre"],
            "orden": d["orden"], "partidos": []})
        gana = None
        fin = d["estado"] == "finalizado"
        if fin:
            w, _l = ko_scoring.winner_loser(d)
            gana = equipos.get(w) if w else None
        fase["partidos"].append({
            "local": equipos.get(d["equipo_local_id"], "Por definir"),
            "visitante": equipos.get(d["equipo_visitante_id"], "Por definir"),
            "gl": d["goles_local"], "gv": d["goles_visitante"],
            "pen_l": d["penales_local"], "pen_v": d["penales_visitante"],
            "ganador": gana, "finalizado": fin})
    ko_out = sorted(ko_map.values(), key=lambda x: x["orden"])

    # 3) Ranking acumulado por fase (matriz apostador × fase + subtotales)
    try:
        rr = await db.execute(
            text("""SELECT apostador_id, fase_tipo, SUM(pts_total)::int AS pts
                    FROM puntaje_detalle WHERE torneo_id=:tid
                    GROUP BY apostador_id, fase_tipo"""),
            {"tid": torneo_id},
        )
        bytipo: dict[int, dict] = {}
        for row in rr.mappings():
            bytipo.setdefault(row["apostador_id"], {})[row["fase_tipo"]] = row["pts"]
    except Exception:
        await db.rollback()
        bytipo = {}

    fases_presentes = [t for t in _PHASE_ORDER if any(t in v for v in bytipo.values())]

    # Incluir TODOS los apostadores activos (rol 'apostador') aunque no tengan
    # puntos: pueden sumarse en una fase posterior y deben figurar en cero.
    async with _app_engine.connect() as conn:
        ar = await conn.execute(
            text("""
                SELECT u.id, u.username FROM users u
                JOIN user_roles ur ON ur.user_id = u.id
                JOIN roles ro ON ro.id = ur.role_id
                WHERE ro.name = 'apostador' AND u.is_active = TRUE
            """))
        usuarios: dict[int, str] = {row["id"]: row["username"] for row in ar.mappings()}
        extra_ids = [i for i in bytipo if i not in usuarios]
        if extra_ids:
            ur = await conn.execute(
                text("SELECT id, username FROM users WHERE id = ANY(:ids)"), {"ids": extra_ids})
            for row in ur.mappings():
                usuarios[row["id"]] = row["username"]
    uids = sorted(set(list(usuarios.keys()) + list(bytipo.keys())))

    apostadores = []
    for uid in uids:
        por: dict[str, dict] = {}
        acc = 0
        for t in fases_presentes:
            pts = bytipo.get(uid, {}).get(t, 0)
            acc += pts
            por[t] = {"pts": pts, "acumulado": acc}
        apostadores.append({
            "apostador_id": uid, "nombre": usuarios.get(uid, f"Usuario {uid}"),
            "por_fase": por, "total": acc,
            "es_actual": uid == current.id})
    apostadores.sort(key=lambda x: (-x["total"], (x["nombre"] or "").lower()))

    # 4) Apuestas y puntajes por fase del apostador seleccionado (default: usuario actual)
    #    Incluye nombres y logos de los equipos para mostrar el partido con banderitas.
    target_uid = apostador_id if apostador_id else current.id
    rm = await db.execute(
        text("""
            SELECT pd.fase_id, pd.fase_tipo, pd.fase_nombre, pd.partido_id, pd.multiplicador,
                   pd.pred_local, pd.pred_visitante, pd.real_local, pd.real_visitante, pd.pts_marcador,
                   pd.pred_minuto, pd.real_minuto, pd.gano_minuto, pd.pts_minuto,
                   pd.pred_amarillas, pd.real_amarillas, pd.pts_amarillas,
                   pd.pred_var, pd.real_var, pd.pts_var, pd.pts_bonus, pd.pts_total,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre,
                   el.logo_url AS local_logo, ev.logo_url AS visit_logo
            FROM puntaje_detalle pd
            LEFT JOIN partido p ON p.id = pd.partido_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE pd.torneo_id=:tid AND pd.apostador_id=:uid
            ORDER BY pd.fase_id, pd.partido_id
        """),
        {"tid": torneo_id, "uid": target_uid},
    )
    mias_map: dict[str, dict] = {}
    for row in rm.mappings():
        d = dict(row)
        f = mias_map.setdefault(d["fase_tipo"], {
            "tipo": d["fase_tipo"],
            "nombre": _PHASE_LABELS_FULL.get(d["fase_tipo"], d["fase_nombre"]),
            "subtotal": 0, "partidos": []})
        f["subtotal"] += d["pts_total"]
        f["partidos"].append(d)
    mias = [mias_map[t] for t in _PHASE_ORDER if t in mias_map]

    return {
        "torneo_id": torneo_id,
        "grupos": grupos_out,
        "ko": ko_out,
        "ranking": {"fases": fases_presentes,
                    "labels": {t: _PHASE_LABELS[t] for t in fases_presentes},
                    "apostadores": apostadores},
        "mias": mias,
        "apostador_sel": target_uid,
        "apostador_sel_nombre": usuarios.get(target_uid, f"Usuario {target_uid}"),
        "apostador_propio": current.id,
    }


@router.get("/transparencia/{torneo_id}/export",
            summary="Exportar a Excel todas las apuestas y puntajes de todos los apostadores (todas las fases)")
async def exportar_transparencia(torneo_id: int, current: CurrentUser, db: DBSession):
    """Genera y descarga el Excel ÚNICO de auditoría (mismo formato que todas las
    salidas): hoja 'Puntaje general' + una hoja por fase con buckets
    Pleno/Ganador/Cero y orden jerárquico de bracket en KO. Cualquier usuario."""
    import io
    wb, _ = await _build_auditoria_workbook(db, torneo_id)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"transparencia_torneo{torneo_id}_{ts}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── Auditoría ────────────────────────────────────────────────────────────────

@router.get("/auditoria/{torneo_id}", summary="Lista de snapshots de auditoría")
async def listar_auditorias(torneo_id: int, current: CurrentUser, db: DBSession) -> list[dict]:
    try:
        r = await db.execute(
            text("""
                SELECT id, torneo_id, generado_at, descripcion, archivo_path
                FROM auditoria_apuestas
                WHERE torneo_id = :tid
                ORDER BY generado_at DESC
            """),
            {"tid": torneo_id}
        )
        rows = [dict(row) for row in r.mappings()]
    except Exception:
        return []  # Tabla no migrada aún

    for row in rows:
        row["generado_at"] = row["generado_at"].isoformat() if row["generado_at"] else None
    return rows


@router.post("/auditoria/{torneo_id}", summary="Generar Excel de auditoría (admin)")
async def generar_auditoria(torneo_id: int, current: CurrentUser, db: DBSession) -> dict:
    if not await _check_admin(current):
        raise HTTPException(403, "Se requiere rol admin o superadmin")

    # Nombre del torneo
    tr = await db.execute(text("SELECT nombre FROM torneo WHERE id=:tid"), {"tid": torneo_id})
    t = tr.one_or_none()
    if not t:
        raise HTTPException(404, "Torneo no encontrado")

    # Conteos para la descripción del snapshot
    rc = await db.execute(
        text("""
            SELECT COUNT(DISTINCT pd.apostador_id) AS aps, COUNT(DISTINCT pd.partido_id) AS pts
            FROM puntaje_detalle pd WHERE pd.torneo_id = :tid
        """),
        {"tid": torneo_id},
    )
    cnt = rc.one_or_none()
    n_aps  = (cnt[0] if cnt else 0) or 0
    n_part = (cnt[1] if cnt else 0) or 0

    # ── Construir Excel ÚNICO (mismo formato que todas las salidas) ──────────
    wb, _ = await _build_auditoria_workbook(db, torneo_id)

    # Guardar en /static/auditorias/
    static_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "static", "auditorias"
    )
    os.makedirs(static_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"auditoria_torneo{torneo_id}_{ts}.xlsx"
    filepath = os.path.join(static_dir, filename)
    wb.save(filepath)

    # Registrar en BD (si la tabla ya existe)
    try:
        await db.execute(
            text("""
                INSERT INTO auditoria_apuestas
                    (torneo_id, generado_por, archivo_path, descripcion)
                VALUES (:tid, :uid, :path, :desc)
            """),
            {
                "tid":  torneo_id,
                "uid":  current.id,
                "path": f"auditorias/{filename}",
                "desc": (f"Snapshot {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}"
                         f" — {n_aps} apostadores, {n_part} partidos"),
            }
        )
        await db.commit()
    except Exception:
        pass  # Tabla no migrada aún; el archivo igual se genera

    return {
        "ok":          True,
        "filename":    filename,
        "apostadores": n_aps,
        "partidos":    n_part,
        "url":         f"/static/auditorias/{filename}",
    }


@router.get("/auditoria/download/{auditoria_id}", summary="Descargar Excel de auditoría")
async def descargar_auditoria(auditoria_id: int, current: CurrentUser, db: DBSession):
    try:
        r = await db.execute(
            text("SELECT archivo_path FROM auditoria_apuestas WHERE id=:aid"),
            {"aid": auditoria_id}
        )
        row = r.one_or_none()
    except Exception:
        raise HTTPException(404, "Tabla de auditoría no disponible")

    if not row:
        raise HTTPException(404, "Auditoría no encontrada")

    static_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "static"
    )
    filepath = os.path.join(static_dir, row[0])
    if not os.path.exists(filepath):
        raise HTTPException(404, "Archivo no encontrado en servidor")

    return FileResponse(
        filepath,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=os.path.basename(filepath),
    )


# ── Mensajes del administrador ───────────────────────────────────────────────

@router.get("/mensajes/{torneo_id}", summary="Mensajes del administrador para los apostadores")
async def get_mensajes(torneo_id: int, db: DBSession) -> list[dict]:
    """Devuelve los mensajes activos del torneo ordenados del más reciente al más antiguo."""
    try:
        r = await db.execute(
            text("""
                SELECT id, numero, titulo, contenido, autor_nombre,
                       created_at AT TIME ZONE 'UTC' AS created_at
                FROM mensaje_admin
                WHERE torneo_id = :tid AND es_activo = TRUE
                ORDER BY numero DESC
            """),
            {"tid": torneo_id},
        )
        rows = r.fetchall()
    except Exception:
        # Si la tabla no existe (migración pendiente) retorna lista vacía
        return []

    return [
        {
            "id":           row.id,
            "numero":       row.numero,
            "titulo":       row.titulo,
            "contenido":    row.contenido,
            "autor_nombre": row.autor_nombre or "Admin",
            "created_at":   row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/mensajes/{torneo_id}", summary="Crear mensaje (solo admin)")
async def create_mensaje(
    torneo_id: int,
    body: MensajeIn,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Crea un mensaje nuevo. Solo accesible para admin y superadmin."""
    # Verificar rol admin
    async with _app_engine.connect() as app_db:
        r = await app_db.execute(
            text("""
                SELECT r.name FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :uid AND r.name IN ('admin','superadmin')
                LIMIT 1
            """),
            {"uid": current_user.id},
        )
        if not r.one_or_none():
            raise HTTPException(403, "Solo administradores pueden crear mensajes")

        # Nombre del autor
        ur = await app_db.execute(
            text("SELECT username, email FROM users WHERE id = :uid"),
            {"uid": current_user.id},
        )
        user_row = ur.one_or_none()
        autor_nombre = (user_row.username or user_row.email) if user_row else "Admin"

    # Siguiente número secuencial para el torneo
    r_num = await db.execute(
        text("SELECT COALESCE(MAX(numero), 0) + 1 FROM mensaje_admin WHERE torneo_id = :tid"),
        {"tid": torneo_id},
    )
    next_num = r_num.scalar() or 1

    r_ins = await db.execute(
        text("""
            INSERT INTO mensaje_admin (numero, torneo_id, titulo, contenido, autor_id, autor_nombre)
            VALUES (:num, :tid, :titulo, :contenido, :uid, :autor)
            RETURNING id, numero, titulo, contenido, autor_nombre,
                      created_at AT TIME ZONE 'UTC' AS created_at
        """),
        {
            "num":      next_num,
            "tid":      torneo_id,
            "titulo":   body.titulo.strip(),
            "contenido": body.contenido.strip(),
            "uid":      current_user.id,
            "autor":    autor_nombre,
        },
    )
    await db.commit()
    row = r_ins.one()
    return {
        "id":           row.id,
        "numero":       row.numero,
        "titulo":       row.titulo,
        "contenido":    row.contenido,
        "autor_nombre": row.autor_nombre,
        "created_at":   row.created_at.isoformat() if row.created_at else None,
    }


@router.delete("/mensajes/{torneo_id}/{mensaje_id}", summary="Eliminar mensaje (solo admin)")
async def delete_mensaje(
    torneo_id: int,
    mensaje_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Desactiva un mensaje (soft delete). Solo admin / superadmin."""
    async with _app_engine.connect() as app_db:
        r = await app_db.execute(
            text("""
                SELECT r.name FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :uid AND r.name IN ('admin','superadmin')
                LIMIT 1
            """),
            {"uid": current_user.id},
        )
        if not r.one_or_none():
            raise HTTPException(403, "Solo administradores pueden eliminar mensajes")

    await db.execute(
        text("""
            UPDATE mensaje_admin
            SET es_activo = FALSE
            WHERE id = :mid AND torneo_id = :tid
        """),
        {"mid": mensaje_id, "tid": torneo_id},
    )
    await db.commit()
    return {"ok": True, "id": mensaje_id}


# ─────────────────────────────────────────────────────────────────────────────
# IMPORTAR APUESTAS — FASE DE GRUPOS
# POST /bets/importar-apuestas-grupos/{torneo_id}
# ─────────────────────────────────────────────────────────────────────────────

class ImportRowIn(BaseModel):
    apostador:            str
    nombre:               str | None = None
    email:                str | None = None
    telefono:             str | None = None
    partido_num:          int
    goles_local:          int
    goles_visitante:      int
    pred_minuto_gol:      int | None = None
    pred_amarillas:       int | None = None
    pred_var:             int | None = None
    pred_rojas:           int | None = None
    pred_penales_partido: int | None = None


@router.post("/importar-apuestas-grupos/{torneo_id}")
async def importar_apuestas_grupos(
    torneo_id: int,
    rows: list[ImportRowIn],
    current: CurrentUser,
    db: DBSession,
    crear_usuarios: bool = False,
):
    """Importa apuestas de fase de grupos desde Excel (admin only)."""
    # Solo admin
    # Admin check usa app_db (user_roles/roles NO existen en becbuc)
    if not await _check_admin(current):
        raise HTTPException(403, "Solo administradores pueden importar apuestas")

    # Verificar torneo
    torneo_r = await db.execute(text("SELECT id FROM torneo WHERE id=:id"), {"id": torneo_id})
    if not torneo_r.one_or_none():
        raise HTTPException(404, f"Torneo {torneo_id} no encontrado")

    # Pre-cargar partidos de fase grupos numerados por f.orden, p.id (igual que generar_excel)
    # La columna 'numero' NO existe en BD — se calcula con ROW_NUMBER().
    # partido_num del Excel puede venir como "P001" o "1" o 1 (int).
    partidos_r = await db.execute(
        text("""
            SELECT p.id,
                   ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE p.torneo_id = :tid AND f.tipo = 'grupo'
            ORDER BY f.orden, p.id
        """),
        {"tid": torneo_id},
    )
    partido_rows = partidos_r.all()
    partido_map = {row.num_seq: row.id for row in partido_rows}
    total_partidos_grupos = len(partido_map)  # para advertencia de cobertura

    # Pre-cargar usuarios existentes (username -> id) — desde app_db
    async with _app_engine.connect() as aconn:
        users_r = await aconn.execute(
            text("SELECT id, username, email FROM users WHERE is_active = TRUE")
        )
        user_map = {row.username.lower(): row.id for row in users_r}

    creadas = 0
    actualizadas = 0
    sin_cambios = 0
    errores = []

    for i, row in enumerate(rows, start=2):
        fila = i

        # 1. Resolver partido — partido_num puede ser int(1) o str("P001"/"1")
        raw_num = row.partido_num
        if isinstance(raw_num, str):
            raw_num = raw_num.strip().lstrip('Pp').lstrip('0') or '0'
        try:
            num_int = int(raw_num)
        except (ValueError, TypeError):
            num_int = None
        partido_id = partido_map.get(num_int) if num_int else None
        if not partido_id:
            errores.append({
                "fila": fila,
                "motivo": f"Partido #{row.partido_num} no encontrado en fase grupos del torneo {torneo_id} "
                          f"(hay {total_partidos_grupos} partidos: P1–P{total_partidos_grupos})",
                "sin_mapeo": True,
            })
            continue

        # 2. Resolver apostador — todas las queries de users van a app_db
        alias = row.apostador.strip().lower()
        user_id = user_map.get(alias)

        if not user_id:
            # Intentar por email si se proveyó
            if row.email:
                async with _app_engine.connect() as aconn:
                    eu = await aconn.execute(
                        text("SELECT id FROM users WHERE email=:e"), {"e": row.email.strip()}
                    )
                    eu_row = eu.one_or_none()
                if eu_row:
                    user_id = eu_row[0]
                    user_map[alias] = user_id

            if not user_id:
                if not crear_usuarios:
                    # Modo seguro: avisar al frontend, no crear automáticamente
                    errores.append({
                        "fila": fila,
                        "motivo": f"Usuario '{row.apostador}' no existe en el sistema",
                        "usuario_faltante": True,
                        "apostador": row.apostador.strip(),
                        "email": row.email or "",
                        "nombre": row.nombre or "",
                        "telefono": row.telefono or "",
                    })
                    continue

                # crear_usuarios=True → crear con contraseña temporal
                if not row.email:
                    errores.append({"fila": fila, "motivo": f"Usuario '{row.apostador}' no existe y no se proporcionó email para crearlo"})
                    continue
                pwd = "mundial2026"
                from app.core.security import hash_password as _hp
                async with _app_engine.begin() as aconn:
                    new_u = await aconn.execute(
                        text("""
                            INSERT INTO users (username, email, nombre, telefono, password_hash, is_active, must_change_password)
                            VALUES (:u, :e, :n, :t, :ph, TRUE, TRUE)
                            ON CONFLICT (username) DO UPDATE SET email=EXCLUDED.email
                            RETURNING id
                        """),
                        {
                            "u": row.apostador.strip(),
                            "e": row.email.strip(),
                            "n": row.nombre,
                            "t": row.telefono,
                            "ph": _hp(pwd),
                        },
                    )
                    user_id = new_u.scalar_one()
                user_map[alias] = user_id

        # 3. Upsert apuesta — en db (becbuc)
        exist_r = await db.execute(
            text("""
                SELECT id, pred_local, pred_visitante, pred_minuto_gol,
                       pred_amarillas, pred_var, pred_rojas, pred_penales_partido
                FROM apuesta
                WHERE partido_id=:pid AND apostador_id=:uid
            """),
            {"pid": partido_id, "uid": user_id},
        )
        exist = exist_r.one_or_none()

        if exist:
            same = (
                exist.pred_local == row.goles_local and
                exist.pred_visitante == row.goles_visitante and
                exist.pred_minuto_gol == row.pred_minuto_gol and
                exist.pred_amarillas == row.pred_amarillas and
                exist.pred_var == row.pred_var and
                exist.pred_rojas == row.pred_rojas and
                exist.pred_penales_partido == row.pred_penales_partido
            )
            if same:
                sin_cambios += 1
                continue
            await db.execute(
                text("""
                    UPDATE apuesta SET
                        pred_local=:l, pred_visitante=:v,
                        pred_minuto_gol=:mg, pred_amarillas=:am,
                        pred_var=:var, pred_rojas=:ro,
                        pred_penales_partido=:pp,
                        updated_at=now()
                    WHERE id=:id
                """),
                {
                    "id": exist.id,
                    "l": row.goles_local, "v": row.goles_visitante,
                    "mg": row.pred_minuto_gol, "am": row.pred_amarillas,
                    "var": row.pred_var, "ro": row.pred_rojas,
                    "pp": row.pred_penales_partido,
                },
            )
            actualizadas += 1
        else:
            await db.execute(
                text("""
                    INSERT INTO apuesta
                        (partido_id, apostador_id,
                         pred_local, pred_visitante,
                         pred_minuto_gol, pred_amarillas, pred_var,
                         pred_rojas, pred_penales_partido,
                         puntos, puntos_bonus, updated_at)
                    VALUES
                        (:pid, :uid,
                         :l, :v, :mg, :am, :var, :ro, :pp,
                         0, 0, now())
                    ON CONFLICT (apostador_id, partido_id) DO UPDATE SET
                        pred_local=EXCLUDED.pred_local,
                        pred_visitante=EXCLUDED.pred_visitante,
                        pred_minuto_gol=EXCLUDED.pred_minuto_gol,
                        pred_amarillas=EXCLUDED.pred_amarillas,
                        pred_var=EXCLUDED.pred_var,
                        pred_rojas=EXCLUDED.pred_rojas,
                        pred_penales_partido=EXCLUDED.pred_penales_partido,
                        updated_at=now()
                """),
                {
                    "pid": partido_id, "uid": user_id,
                    "l": row.goles_local, "v": row.goles_visitante,
                    "mg": row.pred_minuto_gol, "am": row.pred_amarillas,
                    "var": row.pred_var, "ro": row.pred_rojas,
                    "pp": row.pred_penales_partido,
                },
            )
            creadas += 1

    await db.commit()

    # Resetear brackets KO a TBD tras importar grupos
    brackets_reiniciados = 0
    try:
        await _resetear_ko_a_tbd(db, torneo_id)
        await db.commit()
        brackets_reiniciados = 1
    except Exception as _be:
        log.warning("importar_apuestas_grupos.ko_reset_skip", error=str(_be))

    sin_mapeo         = [e for e in errores if e.get("sin_mapeo")]
    usuarios_faltantes = [e for e in errores if e.get("usuario_faltante")]
    otros_errores      = [e for e in errores if not e.get("sin_mapeo") and not e.get("usuario_faltante")]

    advertencias = []
    if sin_mapeo:
        advertencias.append(
            f"{len(sin_mapeo)} filas con partido_num fuera del rango P1-P{total_partidos_grupos} "
            f"(fase grupos tiene {total_partidos_grupos} partidos)"
        )
    if usuarios_faltantes and not crear_usuarios:
        advertencias.append(
            f"{len(usuarios_faltantes)} apostador(es) no existen en el sistema. "
            "Confirmá la creación y volvé a importar con crear_usuarios=true."
        )

    return {
        "ok": True,
        "creadas": creadas,
        "actualizadas": actualizadas,
        "sin_cambios": sin_cambios,
        "errores": otros_errores,
        "sin_mapeo": sin_mapeo,
        "usuarios_faltantes": usuarios_faltantes,
        "advertencias": advertencias,
        "total_partidos_grupos": total_partidos_grupos,
        "brackets_reiniciados": brackets_reiniciados,
    }


@router.get("/contar-apuestas/{torneo_id}", summary="Conteo de apuestas y globales por apostador (admin)")
async def contar_apuestas_por_apostador(
    torneo_id: int,
    current: CurrentUser,
    db: DBSession,
    apostadores: str = "",
) -> dict:
    """Devuelve {alias: {apuestas, globales, usuario_existe}} para verificar antes de importar."""
    if not await _check_admin(current):
        raise HTTPException(403, "Solo administradores")

    aliases = [a.strip().lower() for a in apostadores.split(",") if a.strip()]
    if not aliases:
        return {}

    # Resolver user ids desde app_db
    params = {f"a{i}": a for i, a in enumerate(aliases)}
    placeholders = ", ".join(f":a{i}" for i in range(len(aliases)))
    async with _app_engine.connect() as conn:
        ur = await conn.execute(
            text(f"SELECT id, lower(username) AS uname FROM users WHERE lower(username) IN ({placeholders})"),
            params,
        )
        user_map = {row.uname: row.id for row in ur}

    result = {}
    for alias in aliases:
        uid = user_map.get(alias)
        if not uid:
            result[alias] = {"apuestas": 0, "globales": 0, "usuario_existe": False}
            continue

        cnt = await db.execute(
            text("""
                SELECT COUNT(*) FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                WHERE p.torneo_id = :tid AND a.apostador_id = :uid
            """),
            {"tid": torneo_id, "uid": uid},
        )
        ap_count = int(cnt.scalar() or 0)

        gc = await db.execute(
            text("SELECT COUNT(*) FROM apuesta_global WHERE torneo_id=:tid AND apostador_id=:uid"),
            {"tid": torneo_id, "uid": uid},
        )
        gl_count = int(gc.scalar() or 0)

        result[alias] = {"apuestas": ap_count, "globales": gl_count, "usuario_existe": True}

    return result


@router.post("/inicializar-brackets/{torneo_id}", summary="Inicializar brackets KO a TBD (admin)")
async def inicializar_brackets(torneo_id: int, current: CurrentUser, db: DBSession):
    """Resetea todos los partidos KO del torneo a TBD. Solo admin."""
    if not await _check_admin(current):
        raise HTTPException(403, "Solo administradores pueden inicializar brackets")
    torneo_r = await db.execute(text("SELECT id FROM torneo WHERE id=:id"), {"id": torneo_id})
    if not torneo_r.one_or_none():
        raise HTTPException(404, f"Torneo {torneo_id} no encontrado")
    await _resetear_ko_a_tbd(db, torneo_id)
    await db.commit()
    return {"ok": True, "torneo_id": torneo_id, "msg": "Brackets KO reiniciados a TBD correctamente."}


@router.post("/importar-globales-apostador/{torneo_id}", summary="Importar pronósticos globales A-G para un apostador (admin)")
async def importar_globales_apostador(
    torneo_id: int,
    body: dict,
    current: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Guarda los pronósticos globales A-G para el apostador indicado en body['apostador'].
    Resuelve nombres de equipos a IDs por coincidencia de nombre (normalizado).
    Solo admin. Campos aceptados en body:
      apostador (username, requerido),
      pred_campeon, pred_finalista1, pred_finalista2, pred_peor_equipo,
      pred_goleada_ganador, pred_goleada_perdedor  (nombres de equipo, texto)
      pred_goleador (text), pred_etapa_paraguay (text), pred_goles_paraguay (int)
    """
    import unicodedata, re as _re

    if not await _check_admin(current):
        raise HTTPException(403, "Solo administradores pueden importar globales")

    alias = body.get("apostador", "").strip().lower()
    if not alias:
        raise HTTPException(400, "Campo 'apostador' requerido")

    # Resolver apostador_id desde app_db
    async with _app_engine.connect() as conn:
        ur = await conn.execute(text("SELECT id FROM users WHERE lower(username)=:a"), {"a": alias})
        urow = ur.one_or_none()
    if not urow:
        raise HTTPException(404, f"Apostador '{alias}' no encontrado en el sistema")
    apostador_id = urow[0]

    # Normalizar nombre para matching
    def _norm(s: str) -> str:
        if not s:
            return ""
        s = str(s).lower().strip()
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        s = _re.sub(r"[^a-z0-9 ]", " ", s)
        return _re.sub(r"\s+", " ", s).strip()

    # Cargar equipos del torneo para resolución de nombres.
    # Intento 1: participaciones en fases de grupo.
    r_eq = await db.execute(
        text("""
            SELECT e.id, e.nombre, e.nombre_es
            FROM equipo e
            JOIN participacion pa ON pa.equipo_id = e.id
            JOIN fase f ON f.id = pa.fase_id
            WHERE f.torneo_id = :tid AND f.tipo = 'grupo'
            GROUP BY e.id, e.nombre, e.nombre_es
        """),
        {"tid": torneo_id},
    )
    equipos = list(r_eq.mappings())

    # Intento 2: cualquier partido del torneo (no hay participaciones cargadas aún).
    if not equipos:
        r_eq2 = await db.execute(
            text("""
                SELECT DISTINCT e.id, e.nombre, e.nombre_es
                FROM equipo e
                WHERE e.id IN (
                    SELECT equipo_local_id    FROM partido WHERE torneo_id=:tid AND equipo_local_id IS NOT NULL
                    UNION
                    SELECT equipo_visitante_id FROM partido WHERE torneo_id=:tid AND equipo_visitante_id IS NOT NULL
                )
            """),
            {"tid": torneo_id},
        )
        equipos = list(r_eq2.mappings())

    # Intento 3: todos los equipos en la BD (último recurso).
    if not equipos:
        r_eq3 = await db.execute(text("SELECT id, nombre, nombre_es FROM equipo"))
        equipos = list(r_eq3.mappings())

    def _resolve_equipo(name_text: str) -> int | None:
        if not name_text:
            return None
        norm_input = _norm(name_text)
        # Exact match first
        for e in equipos:
            for campo in [e["nombre_es"] or "", e["nombre"] or ""]:
                if _norm(campo) == norm_input:
                    return e["id"]
        # Substring match
        for e in equipos:
            for campo in [e["nombre_es"] or "", e["nombre"] or ""]:
                nc = _norm(campo)
                if norm_input in nc or nc in norm_input:
                    return e["id"]
        return None

    campeon_id      = _resolve_equipo(body.get("pred_campeon"))
    finalista1_id   = _resolve_equipo(body.get("pred_finalista1"))
    finalista2_id   = _resolve_equipo(body.get("pred_finalista2"))
    peor_equipo_id  = _resolve_equipo(body.get("pred_peor_equipo"))
    goleada_gan_id  = _resolve_equipo(body.get("pred_goleada_ganador"))
    goleada_per_id  = _resolve_equipo(body.get("pred_goleada_perdedor"))

    goleador     = body.get("pred_goleador") or None
    etapa_py     = body.get("pred_etapa_paraguay") or None
    goles_py_raw = body.get("pred_goles_paraguay")
    try:
        goles_py = int(goles_py_raw) if goles_py_raw is not None else None
    except (ValueError, TypeError):
        goles_py = None

    await db.execute(
        text("""
            INSERT INTO apuesta_global
              (torneo_id, apostador_id,
               pred_campeon_id, pred_finalista1_id, pred_finalista2_id,
               pred_goleador, pred_peor_equipo_id,
               pred_goleada_ganador, pred_goleada_perdedor,
               pred_etapa_paraguay, pred_goles_paraguay,
               updated_at)
            VALUES
              (:tid, :uid,
               :campeon, :fin1, :fin2,
               :goleador, :peor,
               :gol_g, :gol_p,
               :etapa, :goles,
               NOW())
            ON CONFLICT (torneo_id, apostador_id) DO UPDATE SET
               pred_campeon_id      = EXCLUDED.pred_campeon_id,
               pred_finalista1_id   = EXCLUDED.pred_finalista1_id,
               pred_finalista2_id   = EXCLUDED.pred_finalista2_id,
               pred_goleador        = EXCLUDED.pred_goleador,
               pred_peor_equipo_id  = EXCLUDED.pred_peor_equipo_id,
               pred_goleada_ganador = EXCLUDED.pred_goleada_ganador,
               pred_goleada_perdedor= EXCLUDED.pred_goleada_perdedor,
               pred_etapa_paraguay  = EXCLUDED.pred_etapa_paraguay,
               pred_goles_paraguay  = EXCLUDED.pred_goles_paraguay,
               updated_at           = NOW()
        """),
        {
            "tid":     torneo_id,
            "uid":     apostador_id,
            "campeon": campeon_id,
            "fin1":    finalista1_id,
            "fin2":    finalista2_id,
            "goleador":goleador,
            "peor":    peor_equipo_id,
            "gol_g":   goleada_gan_id,
            "gol_p":   goleada_per_id,
            "etapa":   etapa_py,
            "goles":   goles_py,
        },
    )
    await db.commit()

    # Contar equipos resueltos para el mensaje
    resueltos_map = {
        "campeon":          campeon_id,
        "finalista1":       finalista1_id,
        "finalista2":       finalista2_id,
        "peor_equipo":      peor_equipo_id,
        "goleada_ganador":  goleada_gan_id,
        "goleada_perdedor": goleada_per_id,
    }
    no_resueltos = [k for k, v in resueltos_map.items() if v is None and body.get(f"pred_{k}")]

    return {
        "ok": True,
        "guardado": True,
        "apostador": alias,
        "apostador_id": apostador_id,
        "msg": f"Pronósticos globales guardados para {alias}",
        "equipos_db": len(equipos),
        "resueltos": resueltos_map,
        "no_resueltos_input": {
            k: body.get(f"pred_{k}") for k in no_resueltos
        },
        "texto": {
            "goleador":         goleador,
            "etapa_paraguay":   etapa_py,
            "goles_paraguay":   goles_py,
        },
    }
