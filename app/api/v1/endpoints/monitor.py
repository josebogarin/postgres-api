"""
endpoints/monitor.py
====================
Endpoints de administración del monitor de partidos.

GET  /monitor/status          → estado del scheduler + semáforo API
GET  /monitor/jornada         → jornada activa + partidos del día
GET  /monitor/log             → últimas N entradas del api_sync_log
POST /monitor/refresh         → forzar tick inmediato
POST /monitor/reiniciar       → re-ejecutar planificador diario
GET  /monitor/config          → ver parámetros actuales
PATCH /monitor/config         → actualizar parámetro en BD
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import BECBUCSession as DBSession, CurrentUser
from app.services.monitor import get_scheduler
from app.services.monitor.persistence import (
    count_api_calls_today,
    get_active_jornada,
    get_api_log_recent,
    get_monitor_config,
    get_partidos_jornada,
    set_monitor_config,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _require_admin(current: CurrentUser) -> None:
    roles = [r.name if hasattr(r, "name") else str(r) for r in (current.roles or [])]
    if not any(r in ("admin", "superadmin") for r in roles):
        raise HTTPException(403, "Se requiere rol admin")


def _dt(val: datetime | None) -> str | None:
    return val.isoformat() if val else None


# ── Schemas ───────────────────────────────────────────────────────────────────

class ConfigPatch(BaseModel):
    key: str
    value: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", summary="Estado del monitor y disponibilidad de la API")
async def monitor_status(current: CurrentUser, db: DBSession) -> dict:
    """
    Retorna:
    - Estado del scheduler (running, jornada_id, ticks, último error).
    - Semáforo de la API externa (verde/rojo + latencia).
    - Cuota de llamadas usada hoy.
    """
    await _require_admin(current)

    sched = get_scheduler()
    if sched is None:
        sched_status = {
            "running": False,
            "activo": False,
            "jornada_id": None,
            "tick_count": 0,
            "last_tick": None,
            "last_error": "Scheduler no inicializado",
        }
        api_ok, api_msg = False, "Scheduler no inicializado"
    else:
        sched_status = sched.status()
        api_ok, api_msg = await sched.check_api()

    calls_hoy = await count_api_calls_today(db)

    return {
        "scheduler":      sched_status,
        "api": {
            "disponible":    api_ok,
            "mensaje":       api_msg,
            "calls_hoy":     calls_hoy,
            "calls_max_dia": sched_status.get("max_calls_dia", 80) if sched else 80,
        },
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/jornada", summary="Jornada activa y estado por partido")
async def monitor_jornada(current: CurrentUser, db: DBSession) -> dict:
    await _require_admin(current)

    jornada = await get_active_jornada(db)
    if not jornada:
        # Intentar por fecha de hoy
        r = await db.execute(
            text("SELECT * FROM monitor_jornada WHERE fecha = CURRENT_DATE"),
        )
        row = r.mappings().first()
        jornada = dict(row) if row else None

    if not jornada:
        return {"jornada": None, "partidos": [], "msg": "Sin jornada registrada hoy"}

    partidos = await get_partidos_jornada(db, jornada["id"])

    # Serializar datetimes
    def _ser(v: object) -> object:
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, date):
            return v.isoformat()
        return v

    return {
        "jornada":  {k: _ser(v) for k, v in jornada.items()},
        "partidos": [{k: _ser(v) for k, v in p.items()} for p in partidos],
    }


@router.get("/log", summary="Últimas llamadas al API externo")
async def monitor_log(
    current: CurrentUser,
    db: DBSession,
    limit: int = 50,
) -> list[dict]:
    await _require_admin(current)
    rows = await get_api_log_recent(db, limit=min(limit, 200))

    def _ser(v: object) -> object:
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    return [{k: _ser(v) for k, v in row.items()} for row in rows]


@router.post("/refresh", summary="Forzar tick inmediato del monitor")
async def monitor_refresh(current: CurrentUser) -> dict:
    await _require_admin(current)
    sched = get_scheduler()
    if sched is None:
        raise HTTPException(503, "Monitor no inicializado")
    return await sched.force_refresh()


@router.post("/reiniciar", summary="Re-ejecutar planificador diario")
async def monitor_reiniciar(current: CurrentUser) -> dict:
    await _require_admin(current)
    sched = get_scheduler()
    if sched is None:
        raise HTTPException(503, "Monitor no inicializado")
    return await sched.reiniciar_planner()


@router.get("/config", summary="Parámetros de configuración del monitor")
async def monitor_config_get(current: CurrentUser, db: DBSession) -> dict:
    await _require_admin(current)
    cfg = await get_monitor_config(db)
    sched = get_scheduler()
    active_cfg = sched.status() if sched else {}
    return {"bd_config": cfg, "runtime_config": active_cfg}


@router.patch("/config", summary="Actualizar un parámetro del monitor en BD")
async def monitor_config_patch(
    body: ConfigPatch,
    current: CurrentUser,
    db: DBSession,
) -> dict:
    await _require_admin(current)
    allowed = {
        "interval_far_seg", "interval_near_seg", "interval_imminent_seg",
        "interval_live_seg", "interval_halftime_seg", "grace_period_seg",
        "max_api_calls_dia", "startup_margin_seg", "monitor_activo",
    }
    if body.key not in allowed:
        raise HTTPException(400, f"Clave '{body.key}' no permitida. Permitidas: {sorted(allowed)}")
    await set_monitor_config(db, body.key, body.value)
    return {"ok": True, "key": body.key, "value": body.value}
