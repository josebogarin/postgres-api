"""
registry.py — Mapa codigo_competencia → ScoringEngine.
Para agregar una nueva competencia: registrar su engine aquí.
El resto del sistema no necesita cambios.

REGLA (sesion 71b): un torneo SIN reglamento propio aplica POR DEFECTO el
reglamento de la Copa del Mundo (copa_mundo_2026). Ademas se emite un WARNING
para avisar al admin que suba el reglamento del torneo en el portal.
"""
from __future__ import annotations
import logging
from .engines.copa_mundo_2026 import CopasMundoScoringEngine
from .engines.default import DefaultScoringEngine  # legacy 3/1/0 (opt-in explicito)

logger = logging.getLogger(__name__)

# Reglamento por defecto cuando la competencia no tiene engine propio.
_DEFAULT_ENGINE: type = CopasMundoScoringEngine

_ENGINES: dict[str, type] = {
    "copa_mundo_2026": CopasMundoScoringEngine,
    "legacy_3_1_0": DefaultScoringEngine,  # disponible solo si se pide explicitamente
    # "champions_2027": ChampionsScoringEngine,  # ← agregar sin tocar el resto
}


def get_engine(codigo_competencia: str | None):
    """
    Devuelve una instancia del engine registrado para el código dado.
    Si el código es None o no está registrado, aplica el reglamento por defecto
    (Copa del Mundo) y emite un WARNING para que el admin suba el reglamento del
    torneo en el portal.
    """
    if codigo_competencia:
        cls = _ENGINES.get(codigo_competencia)
        if cls:
            return cls()
    logger.warning(
        "Competencia '%s' sin reglamento propio -> aplicando reglamento por defecto "
        "(Copa del Mundo). AVISO ADMIN: subir el reglamento del torneo en el portal.",
        codigo_competencia,
    )
    return _DEFAULT_ENGINE()
