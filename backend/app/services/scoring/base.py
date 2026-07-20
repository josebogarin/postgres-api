"""
base.py — Contratos y dataclasses del Scoring Engine.
Todos los engines deben implementar el Protocol ScoringEngine.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


def _wdl(l: int, v: int) -> str:
    """Resultado de un marcador: 'L' gana local, 'E' empate, 'V' gana visitante."""
    return "L" if l > v else ("E" if l == v else "V")


@dataclass
class FaseConfig:
    """Puntos base por tipo de fase (antes de multiplicar x2 por Paraguay)."""
    pts_resultado: int          # H — acertó resultado (gana/empata/pierde)
    pts_marcador_exacto: int    # I — marcador exacto
    pts_amarillas: int = 1      # J
    pts_rojas: int = 1          # K
    pts_var: int = 1            # L
    pts_minuto_gol: int = 1     # N — más cercano al minuto del primer gol
    pts_penales_partido: int = 1         # M — penales sancionados durante el partido
    pts_penales_tanda_por_equipo: int = 2   # O — 2 pts por equipo tanda acertado (0 en grupos)
    pts_equipo_clasifica: int = 0           # P — equipo que clasifica


@dataclass
class ScoringConfig:
    """Configuración completa de reglas para una competencia."""
    nombre: str
    fases: dict  # fase_tipo (str) → FaseConfig
    doble_puntaje_paraguay: bool = False
    # Pronósticos globales (A–G)
    pts_campeon: int = 0                    # A
    pts_finalista_por_equipo: int = 0       # B
    pts_goleador: int = 0                   # C
    pts_peor_equipo: int = 0                # D
    pts_mayor_goleada_ganador: int = 0      # E ganador
    pts_mayor_goleada_perdedor: int = 0     # E perdedor
    pts_etapa_paraguay: int = 0             # F
    pts_goles_paraguay: int = 0             # G


@dataclass
class PartidoScore:
    """Resultado del scoring de UNA apuesta para UN partido."""
    partido_id: int
    apostador_id: int
    fase_tipo: str
    multiplicador: int          # 1 normal, 2 si partido de Paraguay

    # Puntos por concepto (ya incluyen el multiplicador Paraguay)
    pts_resultado: int = 0      # H
    pts_marcador: int = 0       # I (solo si marcador exacto)
    pts_amarillas: int = 0      # J
    pts_rojas: int = 0          # K
    pts_var: int = 0            # L
    pts_minuto: int = 0         # N (calculado externamente, requiere comparar todos)
    pts_penales_partido: int = 0 # M — penales sancionados durante el partido
    pts_penales_tanda: int = 0  # O
    pts_equipo: int = 0         # P

    pts_bonus: int = 0          # J+K+L+N+O+P
    pts_total: int = 0          # H+I+bonus

    # Clasificador para Excel (3=pleno, 1=ganador, 0=cero) — no es el puntaje real
    pts_marcador_base: int = 0
    teams_match: bool = True
    gano_minuto: bool = False


@dataclass
class GlobalScore:
    """Resultado de los pronósticos globales A–G de un apostador."""
    apostador_id: int
    pts_campeon: int = 0        # A
    pts_finalistas: int = 0     # B
    pts_goleador: int = 0       # C
    pts_peor_equipo: int = 0    # D
    pts_mayor_goleada: int = 0  # E
    pts_etapa_paraguay: int = 0 # F
    pts_goles_paraguay: int = 0 # G
    pts_total: int = 0


@runtime_checkable
class ScoringEngine(Protocol):
    """Contrato que debe implementar cada engine de competencia."""

    def get_config(self) -> ScoringConfig:
        ...

    def score_partido(
        self,
        apuesta: dict,
        partido: dict,
        fase_tipo: str,
        es_paraguay: bool = False,
        ko_teams_match: bool = True,
    ) -> PartidoScore:
        """
        Calcula el puntaje de UNA apuesta para UN partido.
        No calcula pts_minuto (requiere comparar todos los apostadores).
        El orquestador (ScoringCalculator) suma pts_minuto después.
        """
        ...

    def score_global(
        self,
        apuesta_global: dict,
        torneo_resultados: dict,
    ) -> GlobalScore:
        """Calcula puntaje de pronósticos globales A–G. Implementado en GRUPO 2."""
        ...
