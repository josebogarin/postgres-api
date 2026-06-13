"""
monitor/poller.py
=================
Lógica de polling inteligente para un partido individual.

Responsabilidades:
  1. Calcular el intervalo apropiado según estado + tiempo al inicio.
  2. Llamar a la API cuando corresponde.
  3. Actualizar la tabla partido + monitor_partido_estado.
  4. (Optionally) disparar recalculo de puntajes si el resultado cambió.

Desacoplado del scheduler: puede testearse sin APScheduler.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

import structlog

from .api_client import ApiFootballClient, parse_fixture_summary
from .config import MonitorConfig
from .state_mapper import (
    MatchState,
    map_api_status,
    is_terminal,
    is_halftime,
    is_live,
    to_db_status,
)
from .persistence import (
    upsert_partido_estado,
    apply_partido_result,
    count_terminales,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Contexto de llamada (para el log)
# ─────────────────────────────────────────────────────────────────────────────

_ESTADO_LABELS: dict[str, str] = {
    "1H":        "⚽ Primer tiempo",
    "HT":        "⏱ Medio tiempo",
    "2H":        "⚽ Segundo tiempo",
    "ET":        "⏱ Prórroga",
    "P":         "🥅 Penales",
    "FT":        "🏁 Finalizado",
    "AET":       "🏁 Finalizado (prórroga)",
    "PEN":       "🏁 Finalizado (penales)",
    "NS":        "📋 Programado",
    "programado":"📋 Programado",
    "en_juego":  "⚽ En juego",
    "finalizado":"🏁 Finalizado",
}


def _derive_context(estado: str | None) -> str | None:
    if not estado:
        return None
    return _ESTADO_LABELS.get(estado)


# ─────────────────────────────────────────────────────────────────────────────
# Cálculo de intervalo
# ─────────────────────────────────────────────────────────────────────────────

def compute_next_interval(
    api_status: str,
    partido_fecha_utc: datetime | None,
    config: MonitorConfig,
) -> int:
    """
    Devuelve el intervalo en segundos hasta la próxima consulta.

    Reglas (en orden de precedencia):
      1. Terminal        → MAX_INT (nunca más)
      2. Live activo     → interval_live_seg
      3. Halftime        → interval_halftime_seg
      4. Programado      → según tiempo al kick-off
    """
    if is_terminal(api_status):
        return 2**31   # efectivamente infinito

    if is_live(api_status) and not is_halftime(api_status):
        return config.interval_live_seg

    if is_halftime(api_status):
        return config.interval_halftime_seg

    # Partido no iniciado: decidir por tiempo restante
    if partido_fecha_utc is None:
        return config.interval_near_seg   # sin fecha: polling moderado

    now = datetime.now(tz=timezone.utc)
    if partido_fecha_utc.tzinfo is None:
        partido_fecha_utc = partido_fecha_utc.replace(tzinfo=timezone.utc)

    diff_min = (partido_fecha_utc - now).total_seconds() / 60.0

    return config.interval_for_minutes_to_start(diff_min)


# ─────────────────────────────────────────────────────────────────────────────
# Poll de un partido
# ─────────────────────────────────────────────────────────────────────────────

async def poll_partido(
    db: "AsyncSession",
    client: ApiFootballClient,
    config: MonitorConfig,
    partido_id: int,
    api_fixture_id: int,
    jornada_id: int,
    partido_fecha_utc: datetime | None,
    prev_estado: str | None = None,
) -> dict:
    """
    Consulta la API para un partido específico y actualiza la BD.

    Retorna un resumen: {api_status, estado_interno, changed, error}.
    """
    contexto = _derive_context(prev_estado)
    result = await client.get_fixture_detail(
        api_fixture_id=api_fixture_id,
        max_calls=config.max_api_calls_dia,
        contexto=contexto,
    )

    now_utc = datetime.now(tz=timezone.utc)

    if not result.ok or not result.data:
        # Error de red o cuota superada
        error_msg = result.error or f"HTTP {result.status_code}"
        log.warning(
            "monitor.poll.error",
            partido_id=partido_id,
            api_fixture_id=api_fixture_id,
            error=error_msg,
        )
        interval = config.interval_near_seg   # reintentar pronto
        await upsert_partido_estado(
            db,
            partido_id=partido_id,
            jornada_id=jornada_id,
            ultima_consulta=now_utc,
            proxima_consulta=now_utc + timedelta(seconds=interval),
            intervalo_seg=interval,
            ultimo_error=error_msg,
            reintentos=1,   # se suma al existente en el trigger del UPDATE
        )
        return {"api_status": "?", "estado_interno": "error", "changed": False, "error": error_msg}

    # Parsear el fixture
    fix_data = parse_fixture_summary(result.data[0]) if result.data else {}
    api_status_raw  = fix_data.get("api_status_raw", "NS")
    goles_local     = fix_data.get("goles_local")
    goles_visitante = fix_data.get("goles_visitante")
    penales_local   = fix_data.get("penales_local")
    penales_visitante = fix_data.get("penales_visitante")
    minuto          = fix_data.get("elapsed")

    state = map_api_status(api_status_raw)
    db_status = to_db_status(state)
    terminal  = is_terminal(api_status_raw)

    # Calcular próximo intervalo
    interval = compute_next_interval(api_status_raw, partido_fecha_utc, config)
    proxima  = now_utc + timedelta(seconds=interval) if not terminal else None

    log.info(
        "monitor.poll.ok",
        partido_id=partido_id,
        api_status=api_status_raw,
        goles=f"{goles_local}-{goles_visitante}",
        minuto=minuto,
        terminal=terminal,
        next_in=f"{interval}s",
    )

    # 1. Actualizar monitor_partido_estado
    await upsert_partido_estado(
        db,
        partido_id=partido_id,
        jornada_id=jornada_id,
        api_status_raw=api_status_raw,
        estado_interno=state.value,
        minuto_actual=minuto,
        goles_local=goles_local,
        goles_visitante=goles_visitante,
        es_terminal=terminal,
        ultima_consulta=now_utc,
        proxima_consulta=proxima,
        intervalo_seg=interval if not terminal else None,
        ultimo_error=None,   # limpiar error previo
    )

    # 2. Actualizar partido en tabla principal
    changed = await apply_partido_result(
        db,
        partido_id=partido_id,
        estado=db_status,
        goles_local=goles_local,
        goles_visitante=goles_visitante,
        minuto_actual=minuto,
        penales_local=penales_local,
        penales_visitante=penales_visitante,
    )

    # 3. Si el resultado cambió y el partido finalizó → disparar recalculo puntajes
    if changed and terminal and db_status == "finalizado":
        try:
            from app.services.scoring.engine import recalcular_partido  # type: ignore
            # Fire-and-forget en background (no bloquear el poll)
            import asyncio
            asyncio.create_task(recalcular_partido(db, partido_id))
        except (ImportError, Exception) as exc:
            log.warning("monitor.poll.scoring_skip", error=str(exc))

    return {
        "api_status": api_status_raw,
        "estado_interno": state.value,
        "changed": changed,
        "terminal": terminal,
        "error": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Check de fin de jornada
# ─────────────────────────────────────────────────────────────────────────────

async def all_terminal(db: "AsyncSession", jornada_id: int) -> bool:
    """True si todos los partidos de la jornada están en estado terminal."""
    total, terminales = await count_terminales(db, jornada_id)
    if total == 0:
        return False
    return total == terminales
