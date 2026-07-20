"""
registry.py — Mapa codigo_competencia → ScoringEngine.
Para agregar una nueva competencia: registrar su engine aquí.
El resto del sistema no necesita cambios.
"""
from __future__ import annotations
from .engines.copa_mundo_2026 import CopasMundoScoringEngine
from .engines.default import DefaultScoringEngine

_ENGINES: dict[str, type] = {
    "copa_mundo_2026": CopasMundoScoringEngine,
    # "liga_local_2027": LigaLocalScoringEngine,  # ← agregar sin tocar el resto
}


def get_engine(codigo_competencia: str | None):
    """
    Devuelve una instancia del engine registrado para el código dado.
    Si el código es None o no está registrado, devuelve el engine default (legacy 3/1/0).
    """
    if codigo_competencia:
        cls = _ENGINES.get(codigo_competencia)
        if cls:
            return cls()
    return DefaultScoringEngine()
