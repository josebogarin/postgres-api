"""
app/services/monitor
====================
Sistema de monitoreo inteligente de partidos del Mundial 2026.

Módulos
-------
config       — parámetros configurables (env + BD)
state_mapper — mapeo de estados API-Football → estados internos
api_client   — cliente HTTP con retry/backoff + log de cuota
persistence  — operaciones DB para jornada, partido y log
poller       — lógica de decisión de intervalo y actualización
scheduler    — integración APScheduler + FastAPI lifespan
"""

from .scheduler import MonitorScheduler, get_scheduler

__all__ = ["MonitorScheduler", "get_scheduler"]
