"""
monitor/persistence.py
======================
Operaciones de base de datos para el sistema de monitoreo.

Todas las funciones reciben una AsyncSession de becbuc (no app_db).
Usan SQL directo (text()) para mantener consistencia con el resto del proyecto.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .api_client import ApiResult

log = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# api_sync_log
# ─────────────────────────────────────────────────────────────────────────────

async def log_api_call(
    db: AsyncSession,
    endpoint: str,
    params: dict,
    result: ApiResult,
    origen: str = "monitor",
    contexto: str | None = None,
) -> None:
    """Persiste un registro de llamada API en api_sync_log."""
    # Derivar contexto de error si no viene del caller
    _ctx = contexto
    if not _ctx and result.error:
        if "cuota" in (result.error or "").lower() or (result.quota_remaining is not None and result.quota_remaining <= 0):
            _ctx = "⛔ Límite de mensajes diarios superado"
        elif result.error:
            _ctx = "🔴 API no responde"
    try:
        await db.execute(
            text("""
                INSERT INTO api_sync_log
                    (endpoint, params, status_code, response_ms, quota_remaining, error_msg, payload_size, origen, contexto)
                VALUES
                    (:ep, :params::jsonb, :sc, :ms, :quota, :err, :size, :origen, :ctx)
            """),
            {
                "ep":     endpoint,
                "params": json.dumps(params),
                "sc":     result.status_code or None,
                "ms":     result.response_ms or None,
                "quota":  result.quota_remaining,
                "err":    result.error,
                "size":   len(json.dumps(result.data)) if result.data else None,
                "origen": origen,
                "ctx":    _ctx,
            },
        )
        await db.commit()
    except Exception as exc:
        log.warning("monitor.log_api_call.error", error=str(exc))
        await db.rollback()


async def get_api_log_recent(db: AsyncSession, limit: int = 50) -> list[dict]:
    """Últimas N entradas del log de API para el panel de diagnóstico."""
    try:
        r = await db.execute(
            text("""
                SELECT id, endpoint, params, status_code, response_ms,
                       quota_remaining, error_msg, origen, contexto, created_at
                FROM api_sync_log
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": limit},
        )
        return [dict(row._mapping) for row in r]
    except Exception as exc:
        log.warning("monitor.get_api_log_recent.error", error=str(exc))
        await db.rollback()
        return []


async def count_api_calls_today(db: AsyncSession) -> int:
    """Cuántas llamadas se hicieron hoy (UTC)."""
    try:
        r = await db.execute(
            text("""
                SELECT COUNT(*) FROM api_sync_log
                WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'UTC')
            """)
        )
        return r.scalar() or 0
    except Exception as exc:
        log.warning("monitor.count_api_calls_today.error", error=str(exc))
        await db.rollback()
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# monitor_config
# ─────────────────────────────────────────────────────────────────────────────

async def get_monitor_config(db: AsyncSession) -> dict[str, str]:
    """Retorna todos los parámetros de monitor_config como dict str→str."""
    try:
        r = await db.execute(text("SELECT key, value FROM monitor_config"))
        return {row.key: row.value for row in r}
    except Exception as exc:
        log.warning("monitor.get_monitor_config.error", error=str(exc))
        await db.rollback()
        return {}


async def set_monitor_config(db: AsyncSession, key: str, value: str) -> None:
    await db.execute(
        text("""
            INSERT INTO monitor_config (key, value, updated_at)
            VALUES (:k, :v, NOW())
            ON CONFLICT (key) DO UPDATE SET value = :v, updated_at = NOW()
        """),
        {"k": key, "v": value},
    )
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# monitor_jornada
# ─────────────────────────────────────────────────────────────────────────────

async def get_or_create_jornada(
    db: AsyncSession,
    fecha: date,
    torneo_id: int | None = None,
) -> dict:
    """
    Obtiene la jornada del día o la crea si no existe.
    Retorna el row como dict.
    """
    r = await db.execute(
        text("SELECT * FROM monitor_jornada WHERE fecha = :f"),
        {"f": fecha},
    )
    row = r.mappings().first()
    if row:
        return dict(row)

    # Crear nueva jornada
    ins = await db.execute(
        text("""
            INSERT INTO monitor_jornada (fecha, torneo_id, estado, created_at, updated_at)
            VALUES (:f, :tid, 'pendiente', NOW(), NOW())
            RETURNING *
        """),
        {"f": fecha, "tid": torneo_id},
    )
    await db.commit()
    return dict(ins.mappings().first())


async def update_jornada(db: AsyncSession, jornada_id: int, **kwargs: Any) -> None:
    """Actualiza campos de una jornada. kwargs son nombre_columna=valor."""
    if not kwargs:
        return
    sets = ", ".join(f"{k} = :{k}" for k in kwargs)
    kwargs["jornada_id"] = jornada_id
    await db.execute(
        text(f"UPDATE monitor_jornada SET {sets}, updated_at = NOW() WHERE id = :jornada_id"),
        kwargs,
    )
    await db.commit()


async def get_jornada_by_fecha(db: AsyncSession, fecha: date) -> dict | None:
    r = await db.execute(
        text("SELECT * FROM monitor_jornada WHERE fecha = :f"),
        {"f": fecha},
    )
    row = r.mappings().first()
    return dict(row) if row else None


async def get_active_jornada(db: AsyncSession) -> dict | None:
    """Jornada activa hoy (estado 'activo')."""
    r = await db.execute(
        text("""
            SELECT * FROM monitor_jornada
            WHERE estado IN ('activo', 'pendiente')
              AND fecha >= CURRENT_DATE
            ORDER BY fecha
            LIMIT 1
        """)
    )
    row = r.mappings().first()
    return dict(row) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# monitor_partido_estado
# ─────────────────────────────────────────────────────────────────────────────

async def upsert_partido_estado(
    db: AsyncSession,
    partido_id: int,
    jornada_id: int | None = None,
    **kwargs: Any,
) -> None:
    """
    Crea o actualiza el estado de polling de un partido.
    kwargs: api_status_raw, estado_interno, minuto_actual, goles_local,
            goles_visitante, es_terminal, ultima_consulta, proxima_consulta,
            intervalo_seg, ultimo_error, reintentos
    """
    fields = {k: v for k, v in kwargs.items() if v is not None or k in (
        "minuto_actual", "ultimo_error", "goles_local", "goles_visitante"
    )}

    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    if set_clause:
        set_clause += ", "
    set_clause += "updated_at = NOW(), consultas_totales = consultas_totales + 1"

    params = {"pid": partido_id, "jid": jornada_id, **fields}

    await db.execute(
        text(f"""
            INSERT INTO monitor_partido_estado
                (partido_id, jornada_id, consultas_totales, created_at, updated_at)
            VALUES (:pid, :jid, 1, NOW(), NOW())
            ON CONFLICT (partido_id) DO UPDATE
            SET {set_clause}
        """),
        params,
    )
    await db.commit()


async def get_partido_estado(db: AsyncSession, partido_id: int) -> dict | None:
    r = await db.execute(
        text("SELECT * FROM monitor_partido_estado WHERE partido_id = :pid"),
        {"pid": partido_id},
    )
    row = r.mappings().first()
    return dict(row) if row else None


async def get_partidos_pendientes_poll(
    db: AsyncSession,
    jornada_id: int,
    now_utc: datetime,
) -> list[dict]:
    """
    Partidos de la jornada que NO son terminales y cuya proxima_consulta <= now.
    Incluye datos del partido (fecha, api_fixture_id) para la lógica de intervalo.
    """
    r = await db.execute(
        text("""
            SELECT
                mpe.partido_id,
                mpe.api_status_raw,
                mpe.estado_interno,
                mpe.es_terminal,
                mpe.proxima_consulta,
                mpe.consultas_totales,
                mpe.reintentos,
                p.fecha          AS partido_fecha,
                p.api_fixture_id,
                p.estado         AS db_estado
            FROM monitor_partido_estado mpe
            JOIN partido p ON p.id = mpe.partido_id
            WHERE mpe.jornada_id = :jid
              AND mpe.es_terminal = FALSE
              AND (mpe.proxima_consulta IS NULL OR mpe.proxima_consulta <= :now)
            ORDER BY p.fecha NULLS LAST
        """),
        {"jid": jornada_id, "now": now_utc},
    )
    return [dict(row._mapping) for row in r]


async def get_partidos_jornada(
    db: AsyncSession,
    jornada_id: int,
) -> list[dict]:
    """Todos los partidos de una jornada con su estado de monitoreo."""
    r = await db.execute(
        text("""
            SELECT
                p.id, p.fecha, p.estado AS db_estado, p.api_fixture_id,
                COALESCE(p.amarillas, 0) AS amarillas,
                COALESCE(p.rojas, 0) AS rojas,
                COALESCE(p.decisiones_var, 0) AS decisiones_var,
                COALESCE(p.penales_partido, 0) AS penales_partido,
                COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                COALESCE(ev.nombre_es, ev.nombre) AS visita_nombre,
                el.logo_url AS local_logo, ev.logo_url AS visita_logo,
                COALESCE(el.codigo_iso, '') AS local_iso,
                COALESCE(ev.codigo_iso, '') AS visita_iso,
                mpe.api_status_raw, mpe.estado_interno, mpe.minuto_actual,
                mpe.goles_local, mpe.goles_visitante,
                mpe.es_terminal, mpe.ultima_consulta, mpe.proxima_consulta,
                mpe.consultas_totales, mpe.intervalo_seg, mpe.ultimo_error
            FROM monitor_partido_estado mpe
            JOIN partido p         ON p.id = mpe.partido_id
            JOIN equipo el         ON el.id = p.equipo_local_id
            JOIN equipo ev         ON ev.id = p.equipo_visitante_id
            WHERE mpe.jornada_id = :jid
            ORDER BY p.fecha NULLS LAST, p.id
        """),
        {"jid": jornada_id},
    )
    return [dict(row._mapping) for row in r]


async def count_terminales(db: AsyncSession, jornada_id: int) -> tuple[int, int]:
    """Retorna (total, terminales) para la jornada."""
    r = await db.execute(
        text("""
            SELECT
                COUNT(*)                           AS total,
                COUNT(*) FILTER (WHERE es_terminal) AS terminales
            FROM monitor_partido_estado
            WHERE jornada_id = :jid
        """),
        {"jid": jornada_id},
    )
    row = r.first()
    return (row[0] or 0, row[1] or 0)


async def init_partidos_jornada(
    db: AsyncSession,
    jornada_id: int,
    partido_ids: list[int],
) -> None:
    """Crea entradas en monitor_partido_estado para los partidos de la jornada."""
    for pid in partido_ids:
        await db.execute(
            text("""
                INSERT INTO monitor_partido_estado
                    (partido_id, jornada_id, estado_interno, es_terminal,
                     consultas_totales, created_at, updated_at)
                VALUES (:pid, :jid, 'programado', FALSE, 0, NOW(), NOW())
                ON CONFLICT (partido_id) DO UPDATE
                SET jornada_id = :jid, updated_at = NOW()
            """),
            {"pid": pid, "jid": jornada_id},
        )
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Actualizar partido en la tabla principal (becbuc.partido)
# ─────────────────────────────────────────────────────────────────────────────

async def apply_partido_result(
    db: AsyncSession,
    partido_id: int,
    *,
    estado: str,
    goles_local: int | None,
    goles_visitante: int | None,
    minuto_actual: int | None,
    penales_local: int | None = None,
    penales_visitante: int | None = None,
) -> bool:
    """
    Actualiza partido.estado, goles y minuto_actual.
    Retorna True si hubo cambio real (para triggear recalculo de puntajes).
    """
    r = await db.execute(
        text("SELECT estado, goles_local, goles_visitante FROM partido WHERE id = :id"),
        {"id": partido_id},
    )
    prev = r.first()
    if not prev:
        return False

    changed = (
        prev[0] != estado
        or prev[1] != goles_local
        or prev[2] != goles_visitante
    )

    await db.execute(
        text("""
            UPDATE partido
            SET estado = :estado,
                goles_local = :gl,
                goles_visitante = :gv,
                minuto_actual = :minuto,
                penales_local = COALESCE(:pl, penales_local),
                penales_visitante = COALESCE(:pv, penales_visitante)
            WHERE id = :id
        """),
        {
            "id":     partido_id,
            "estado": estado,
            "gl":     goles_local,
            "gv":     goles_visitante,
            "minuto": minuto_actual,
            "pl":     penales_local,
            "pv":     penales_visitante,
        },
    )
    await db.commit()
    return changed


async def get_partidos_del_dia(
    db: AsyncSession,
    torneo_id: int,
    fecha: date,
) -> list[dict]:
    """
    Partidos del torneo en una fecha dada (comparando la parte de fecha del campo fecha).
    """
    r = await db.execute(
        text("""
            SELECT
                               p.id, p.fecha, p.estado,
                p.goles_local, p.goles_visitante,
                COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                COALESCE(ev.nombre_es, ev.nombre) AS visita_nombre,
                el.logo_url AS local_logo, ev.logo_url AS visita_logo
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid
              AND DATE(p.fecha AT TIME ZONE 'UTC') = :fecha
            ORDER BY p.fecha NULLS LAST
        """),
        {"tid": torneo_id, "fecha": fecha},
    )
    return [dict(row._mapping) for row in r]
