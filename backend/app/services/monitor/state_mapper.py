"""
monitor/state_mapper.py
=======================
Mapeo de estados API-Football → estados internos BECBUC.

Principio de diseño: capa de traducción desacoplada del proveedor.
Si se cambia la API de fútbol, solo se actualiza este módulo.
"""

from __future__ import annotations

from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# Estado interno normalizado
# ─────────────────────────────────────────────────────────────────────────────
class MatchState(str, Enum):
    SCHEDULED   = "programado"
    LIVE        = "en_juego"
    HALFTIME    = "descanso"    # HT / BT — entre períodos
    FINISHED    = "finalizado"
    POSTPONED   = "aplazado"
    CANCELLED   = "suspendido"
    UNKNOWN     = "desconocido"


# ─────────────────────────────────────────────────────────────────────────────
# Conjuntos de estados API-Football v3
# Referencia: https://www.api-football.com/documentation-v3#tag/Fixtures/operation/get-fixtures
# ─────────────────────────────────────────────────────────────────────────────

# Partidos definitivamente terminados con resultado válido
_API_FINISHED = {"FT", "AET", "PEN"}

# Partidos cancelados / sin resultado oficial
_API_CANCELLED = {"CANC", "ABD", "SUSP", "INT", "AWD", "WO"}

# Partido postpuesto (no cancelado — puede reagendarse)
_API_POSTPONED = {"PST", "TBD"}

# En descanso entre períodos
_API_HALFTIME = {"HT", "BT"}

# En juego activo
_API_LIVE = {"1H", "2H", "ET", "P", "LIVE", "BREAK"}

# Programado / no iniciado
_API_SCHEDULED = {"NS"}

# Terminales a efectos de polling (no tiene sentido seguir consultando)
_API_TERMINAL = _API_FINISHED | _API_CANCELLED


# ─────────────────────────────────────────────────────────────────────────────
# Mapa API status → estado interno BECBUC (tabla partido.estado)
# ─────────────────────────────────────────────────────────────────────────────
_DB_STATUS: dict[MatchState, str] = {
    MatchState.SCHEDULED: "programado",
    MatchState.LIVE:      "en_juego",
    MatchState.HALFTIME:  "en_juego",   # BECBUC no distingue descanso en partido.estado
    MatchState.FINISHED:  "finalizado",
    MatchState.POSTPONED: "aplazado",
    MatchState.CANCELLED: "suspendido",
    MatchState.UNKNOWN:   "programado",
}


# ─────────────────────────────────────────────────────────────────────────────
# API pública del módulo
# ─────────────────────────────────────────────────────────────────────────────

def map_api_status(api_status: str) -> MatchState:
    """Traduce un status de API-Football a MatchState interno."""
    s = (api_status or "").upper().strip()
    if s in _API_FINISHED:
        return MatchState.FINISHED
    if s in _API_CANCELLED:
        return MatchState.CANCELLED
    if s in _API_POSTPONED:
        return MatchState.POSTPONED
    if s in _API_HALFTIME:
        return MatchState.HALFTIME
    if s in _API_LIVE:
        return MatchState.LIVE
    if s in _API_SCHEDULED:
        return MatchState.SCHEDULED
    return MatchState.UNKNOWN


def is_terminal(api_status: str) -> bool:
    """True si el partido está en estado terminal (no hay más polling)."""
    return (api_status or "").upper().strip() in _API_TERMINAL


def is_live(api_status: str) -> bool:
    """True si el partido está actualmente en juego (incluyendo descanso)."""
    s = (api_status or "").upper().strip()
    return s in _API_LIVE | _API_HALFTIME


def is_halftime(api_status: str) -> bool:
    return (api_status or "").upper().strip() in _API_HALFTIME


def to_db_status(state: MatchState) -> str:
    """Traduce MatchState al valor de partido.estado en BECBUC."""
    return _DB_STATUS.get(state, "programado")


def describe_state(api_status: str) -> str:
    """Descripción legible del estado para logs y UI."""
    _LABELS: dict[str, str] = {
        "NS":   "No iniciado",
        "1H":   "1er tiempo",
        "HT":   "Descanso",
        "2H":   "2do tiempo",
        "ET":   "Prórroga",
        "BT":   "Entre tiempos extra",
        "P":    "Penales",
        "FT":   "Finalizado",
        "AET":  "Finalizado (prórr.)",
        "PEN":  "Finalizado (pens.)",
        "PST":  "Postergado",
        "CANC": "Cancelado",
        "SUSP": "Suspendido",
        "ABD":  "Abandonado",
        "AWD":  "Por walkover",
        "WO":   "Por walkover",
        "INT":  "Interrumpido",
        "TBD":  "Hora a confirmar",
        "LIVE": "En vivo",
    }
    return _LABELS.get((api_status or "").upper().strip(), api_status or "?")
