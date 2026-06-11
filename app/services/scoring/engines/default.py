"""
default.py — Engine legacy 3/1/0 con multiplicador por fase.
Fallback para competencias sin engine específico registrado.
Mantiene el comportamiento histórico del sistema.

  Marcador exacto:  3 pts × PHASE_MULT
  Resultado:        1 pt  × PHASE_MULT
  Fallo:            0 pts
  Bonus J/L/N:      1 pt  × PHASE_MULT
"""
from __future__ import annotations
from ..base import FaseConfig, ScoringConfig, PartidoScore, GlobalScore, _wdl

# Multiplicadores legacy por fase (mismo mapa que ko_scoring.PHASE_MULT)
_PHASE_MULT: dict[str, int] = {
    "grupo":         1,
    "ronda32":       2,
    "ronda16":       4,
    "cuartos":       8,
    "semis":         16,
    "tercer_puesto": 16,
    "final":         32,
}

# FaseConfig simbólico (default no usa puntos escalados, usa PHASE_MULT)
_FASES = {k: FaseConfig(pts_resultado=1, pts_marcador_exacto=3) for k in _PHASE_MULT}

CONFIG = ScoringConfig(
    nombre="Default Legacy 3/1/0",
    fases=_FASES,
    doble_puntaje_paraguay=False,
)


class DefaultScoringEngine:
    """
    Engine legacy 3/1/0 × PHASE_MULT.
    Usado como fallback para competencias sin engine registrado.
    """

    def get_config(self) -> ScoringConfig:
        return CONFIG

    def score_partido(
        self,
        apuesta: dict,
        partido: dict,
        fase_tipo: str,
        es_paraguay: bool = False,
        ko_teams_match: bool = True,
    ) -> PartidoScore:
        mult = _PHASE_MULT.get(fase_tipo, 1)

        score = PartidoScore(
            partido_id=partido["id"],
            apostador_id=apuesta["apostador_id"],
            fase_tipo=fase_tipo,
            multiplicador=mult,
            teams_match=ko_teams_match,
        )

        if not ko_teams_match:
            return score

        pl = apuesta.get("pred_local")
        pv = apuesta.get("pred_visitante")
        rl = partido.get("goles_local")
        rv = partido.get("goles_visitante")

        if None in (pl, pv, rl, rv):
            return score

        # Marcador (3/1/0)
        if pl == rl and pv == rv:
            base = 3
        elif _wdl(pl, pv) == _wdl(rl, rv):
            base = 1
        else:
            base = 0

        score.pts_marcador_base = base
        # En default, pts_marcador almacena base*mult (no separamos H de I)
        score.pts_marcador = base * mult

        # Bonus J (amarillas)
        if (apuesta.get("pred_amarillas") is not None
                and partido.get("amarillas") is not None
                and apuesta["pred_amarillas"] == partido["amarillas"]):
            score.pts_amarillas = 1 * mult

        # Bonus L (VAR)
        if (apuesta.get("pred_var") is not None
                and partido.get("decisiones_var") is not None
                and apuesta["pred_var"] == partido["decisiones_var"]):
            score.pts_var = 1 * mult

        # N (minuto) se suma externamente

        score.pts_bonus = score.pts_amarillas + score.pts_var
        score.pts_total = score.pts_marcador + score.pts_bonus

        return score

    def score_global(self, apuesta_global: dict, torneo_resultados: dict) -> GlobalScore:
        return GlobalScore(apostador_id=apuesta_global.get("apostador_id", 0))
