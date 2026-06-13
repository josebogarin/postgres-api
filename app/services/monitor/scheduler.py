"""
monitor/scheduler.py
====================
Integración APScheduler + FastAPI lifespan.

Arquitectura de jobs:
  - monitor_daily_planner  → corre 1x/día, planifica la jornada
  - monitor_tick           → corre cada 30 s, decide qué partidos consultar

El scheduler arranca en el lifespan de FastAPI y se detiene al salir.
Estado de la jornada activa se persiste en BD para sobrevivir reinicios.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.db.session import AsyncBecbucSession

from .api_client import ApiFootballClient
from .config import MonitorConfig
from .persistence import (
    count_terminales,
    get_active_jornada,
    get_or_create_jornada,
    get_partidos_del_dia,
    get_partidos_pendientes_poll,
    init_partidos_jornada,
    log_api_call,
    update_jornada,
)
from .poller import all_terminal, poll_partido

log = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Singleton del scheduler
# ─────────────────────────────────────────────────────────────────────────────
_scheduler: "MonitorScheduler | None" = None


def get_scheduler() -> "MonitorScheduler | None":
    return _scheduler


class MonitorScheduler:
    """
    Gestiona el ciclo de vida del monitor de partidos.

    - start(): llama desde FastAPI lifespan.
    - stop():  llama al finalizar.
    - force_refresh(): para el botón de refresh manual en el panel admin.
    - status():        para el panel de diagnóstico.
    """

    def __init__(self, config: MonitorConfig | None = None):
        self.config = config or MonitorConfig.from_env()
        self._aps = AsyncIOScheduler(timezone="UTC")
        self._client: ApiFootballClient | None = None
        self._grace_timer_task: asyncio.Task | None = None
        # Estado en memoria para el panel de diagnóstico
        self._last_tick: datetime | None = None
        self._last_error: str | None = None
        self._jornada_id: int | None = None
        self._tick_count: int = 0

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.config.monitor_activo:
            log.info("monitor.disabled_by_config")
            return
        if not settings.APIFOOTBALL_KEY or settings.APIFOOTBALL_KEY == "TU_API_KEY_AQUI":
            log.warning("monitor.no_api_key")
            return

        global _scheduler
        _scheduler = self

        # Cliente HTTP persistente (reutiliza conexiones)
        self._client = ApiFootballClient(
            timeout=self.config.api_timeout,
            max_retries=self.config.max_retries,
            backoff_base=self.config.retry_backoff_base,
        )
        await self._client.__aenter__()

        # Inyectar callback de logging
        async def _log_cb(ep: str, params: dict, result: Any, origen: str, contexto: str | None = None) -> None:
            async with AsyncBecbucSession() as db:
                await log_api_call(db, ep, params, result, origen, contexto=contexto)

        self._client.set_log_callback(_log_cb)

        # Job 1: planificador diario — corre a las 00:05 UTC + al arrancar
        self._aps.add_job(
            self._daily_planner,
            CronTrigger(hour=0, minute=5, timezone="UTC"),
            id="monitor_daily_planner",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Job 2: tick principal — cada 30 s
        self._aps.add_job(
            self._tick,
            IntervalTrigger(seconds=self.config.tick_seg),
            id="monitor_tick",
            replace_existing=True,
            misfire_grace_time=30,
        )

        self._aps.start()
        log.info("monitor.scheduler.started", tick_seg=self.config.tick_seg)

        # Ejecutar el planificador diario al arrancar (recupera jornada existente)
        asyncio.create_task(self._daily_planner())

    async def stop(self) -> None:
        if self._aps.running:
            self._aps.shutdown(wait=False)
        if self._client:
            await self._client.__aexit__(None, None, None)
        log.info("monitor.scheduler.stopped")

    # ── Planificador diario ───────────────────────────────────────────────────

    async def _daily_planner(self) -> None:
        """
        Obtiene los partidos del día y registra la jornada en BD.
        Si ya existe una jornada activa con partidos, la reanuda.
        """
        today = date.today()
        log.info("monitor.planner.start", fecha=today.isoformat())

        # Obtener torneo activo
        torneo_id = await self._get_active_torneo_id()
        if not torneo_id:
            log.info("monitor.planner.no_active_torneo")
            return

        try:
            async with AsyncBecbucSession() as db:
                jornada = await get_or_create_jornada(db, today, torneo_id)
                jornada_id = jornada["id"]
                self._jornada_id = jornada_id

                # Obtener partidos del día desde BD (ya fueron cargados via fixture)
                partidos = await get_partidos_del_dia(db, torneo_id, today)

                if not partidos:
                    log.info("monitor.planner.no_partidos_hoy", fecha=today.isoformat())
                    await update_jornada(db, jornada_id, estado="omitido",
                                        notas="Sin partidos este día")
                    return

                # Filtrar los que tienen api_fixture_id mapeado
                con_api = [p for p in partidos if p.get("api_fixture_id")]
                sin_api = [p for p in partidos if not p.get("api_fixture_id")]

                if sin_api:
                    log.warning(
                        "monitor.planner.sin_api_fixture",
                        count=len(sin_api),
                        partidos=[p["id"] for p in sin_api],
                    )

                # Inicializar estado de polling para los partidos del día
                await init_partidos_jornada(db, jornada_id, [p["id"] for p in con_api])

                # Calcular inicio y fin de la jornada
                fechas = [p["fecha"] for p in con_api if p.get("fecha")]
                primer = min(fechas) if fechas else None
                ultimo  = max(fechas) if fechas else None

                await update_jornada(
                    db,
                    jornada_id,
                    estado="activo",
                    total_partidos=len(con_api),
                    primer_partido_utc=primer,
                    ultimo_partido_utc=ultimo,
                    iniciado_en=datetime.now(tz=timezone.utc),
                    ultima_actividad=datetime.now(tz=timezone.utc),
                )

                log.info(
                    "monitor.planner.done",
                    jornada_id=jornada_id,
                    partidos=len(con_api),
                    primer=str(primer),
                    ultimo=str(ultimo),
                )

        except Exception as exc:
            self._last_error = str(exc)
            log.error("monitor.planner.error", error=str(exc), exc_info=True)

    # ── Tick principal ────────────────────────────────────────────────────────

    async def _tick(self) -> None:
        """
        Corre cada 30 s. Consulta API para los partidos que corresponde.
        """
        self._tick_count += 1
        self._last_tick = datetime.now(tz=timezone.utc)

        if self._jornada_id is None:
            # Intentar recuperar jornada activa desde BD (si hubo reinicio)
            try:
                async with AsyncBecbucSession() as db:
                    j = await get_active_jornada(db)
                    if j:
                        self._jornada_id = j["id"]
                    else:
                        return
            except Exception:
                return

        try:
            async with AsyncBecbucSession() as db:
                now_utc = datetime.now(tz=timezone.utc)

                # Obtener partidos que necesitan ser consultados ahora
                pendientes = await get_partidos_pendientes_poll(
                    db, self._jornada_id, now_utc
                )

                if not pendientes:
                    # Verificar si la jornada terminó
                    if await all_terminal(db, self._jornada_id):
                        await self._handle_jornada_complete(db)
                    return

                log.debug(
                    "monitor.tick",
                    n=len(pendientes),
                    tick=self._tick_count,
                )

                # Actualizar actividad
                await update_jornada(db, self._jornada_id,
                                     ultima_actividad=now_utc)

            # Pollear cada partido que corresponde
            for partido_row in pendientes:
                if not partido_row.get("api_fixture_id"):
                    continue
                await self._poll_one(partido_row)

            # Después de pollear, chequear si quedaron todos terminales
            async with AsyncBecbucSession() as db:
                terminales = await all_terminal(db, self._jornada_id)
                if terminales and self._grace_timer_task is None:
                    asyncio.create_task(self._grace_period_then_close())

        except Exception as exc:
            self._last_error = str(exc)
            log.error("monitor.tick.error", error=str(exc), exc_info=True)

    async def _poll_one(self, partido_row: dict) -> None:
        """Pollea un partido individual. Crea su propia sesión de BD."""
        assert self._client is not None

        fecha_utc: datetime | None = None
        if partido_row.get("partido_fecha"):
            f = partido_row["partido_fecha"]
            if isinstance(f, str):
                fecha_utc = datetime.fromisoformat(f)
            else:
                fecha_utc = f
            if fecha_utc and fecha_utc.tzinfo is None:
                fecha_utc = fecha_utc.replace(tzinfo=timezone.utc)

        try:
            async with AsyncBecbucSession() as db:
                await poll_partido(
                    db=db,
                    client=self._client,
                    config=self.config,
                    partido_id=partido_row["partido_id"],
                    api_fixture_id=partido_row["api_fixture_id"],
                    jornada_id=self._jornada_id,
                    partido_fecha_utc=fecha_utc,
                    prev_estado=partido_row.get("estado_interno"),
                )
        except Exception as exc:
            self._last_error = str(exc)
            log.error("monitor.poll_one.error",
                      partido_id=partido_row.get("partido_id"),
                      error=str(exc))

    # ── Fin de jornada ────────────────────────────────────────────────────────

    async def _grace_period_then_close(self) -> None:
        """
        Espera el grace period, hace una verificación final y cierra la jornada.
        """
        grace = self.config.grace_period_seg
        log.info("monitor.grace_period.start", segundos=grace)
        await asyncio.sleep(grace)

        log.info("monitor.grace_period.final_check")
        # Poll final de todos los partidos de la jornada para confirmar estado
        try:
            async with AsyncBecbucSession() as db:
                now_utc = datetime.now(tz=timezone.utc)
                pendientes = await get_partidos_pendientes_poll(
                    db, self._jornada_id, now_utc + timedelta(hours=24)
                )

            # Force-poll todos los no-terminales
            for p in pendientes:
                if p.get("api_fixture_id"):
                    await self._poll_one(p)

            async with AsyncBecbucSession() as db:
                if await all_terminal(db, self._jornada_id):
                    await self._handle_jornada_complete(db)

        except Exception as exc:
            log.error("monitor.grace_period.error", error=str(exc))
        finally:
            self._grace_timer_task = None

    async def _handle_jornada_complete(self, db: Any) -> None:
        total, terminales = await count_terminales(db, self._jornada_id)
        log.info("monitor.jornada.complete",
                 jornada_id=self._jornada_id,
                 total=total, terminales=terminales)
        await update_jornada(
            db,
            self._jornada_id,
            estado="terminado",
            partidos_terminales=terminales,
            terminado_en=datetime.now(tz=timezone.utc),
            notas=f"Todos los partidos terminales ({terminales}/{total})",
        )
        self._jornada_id = None   # limpiar para que el tick deje de correr

    # ── API pública (para endpoints admin) ───────────────────────────────────

    async def force_refresh(self) -> dict:
        """Fuerza un tick inmediato y retorna resumen."""
        if not self._jornada_id:
            return {"ok": False, "msg": "Sin jornada activa"}
        await self._tick()
        return {
            "ok": True,
            "jornada_id": self._jornada_id,
            "tick": self._tick_count,
            "last_tick": self._last_tick.isoformat() if self._last_tick else None,
        }

    async def reiniciar_planner(self) -> dict:
        """Re-ejecuta el planificador diario manualmente."""
        asyncio.create_task(self._daily_planner())
        return {"ok": True, "msg": "Planificador iniciado"}

    def status(self) -> dict:
        return {
            "running":       self._aps.running,
            "activo":        self.config.monitor_activo,
            "jornada_id":    self._jornada_id,
            "tick_count":    self._tick_count,
            "last_tick":     self._last_tick.isoformat() if self._last_tick else None,
            "last_error":    self._last_error,
            "tick_seg":      self.config.tick_seg,
            "grace_period":  self.config.grace_period_seg,
            "max_calls_dia": self.config.max_api_calls_dia,
            "league_id":     self.config.league_id,
            "season":        self.config.season,
        }

    async def check_api(self) -> tuple[bool, str]:
        """Prueba conectividad con la API. Para el semáforo del panel."""
        if not self._client:
            return False, "Cliente no inicializado"
        return await self._client.check_api_available()

    # ── Helper privado ────────────────────────────────────────────────────────

    async def _get_active_torneo_id(self) -> int | None:
        """Obtiene el id del torneo activo en la BD."""
        try:
            from sqlalchemy import text
            async with AsyncBecbucSession() as db:
                r = await db.execute(
                    text("""
                        SELECT t.id FROM torneo t
                        JOIN competicion c ON c.id = t.competicion_id
                        WHERE t.estado IN ('en_curso', 'activo')
                          AND c.api_league_id = :lid
                        ORDER BY t.anio DESC
                        LIMIT 1
                    """),
                    {"lid": self.config.league_id},
                )
                row = r.first()
                return row[0] if row else None
        except Exception as exc:
            log.error("monitor.get_torneo.error", error=str(exc))
            return None
