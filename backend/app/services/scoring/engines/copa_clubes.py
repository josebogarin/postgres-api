"""
copa_clubes.py — Engine de torneos de CLUBES (Libertadores / Sudamericana).
Reglamento nuevo (Opción C). Series a ida y vuelta, sin 3er puesto.

Este engine cubre el puntaje POR PARTIDO (una pierna). Los multiplicadores de
SERIE (cruce, comodín, definición por penales, minuto ×2) los aplica el
orquestador de clubes, no este engine — acá está la tabla de puntos base.

Tabla de puntos base por fase:
  Concepto                         | Octavos | Cuartos | Semis | Final
  H  Resultado (gana/empata/pierde)|    4    |   12    |   30  |   75
  I  Marcador exacto (acumula H)   |    8    |   24    |   60  |  150
  Rojas / Amarillas / Pen. en juego|    3    |    5    |    8  |   12   (exacto y ≥1 evento)
  Sustituciones (TOTAL del partido)|    3    |    5    |    8  |   12   (exacto y ≥1 cambio)

Minuto del primer gol: si se acierta, el partido vale el DOBLE (lo aplica el
  orquestador porque el ganador del minuto se decide comparando a todos).

Fases en la BD de clubes:
  'ronda32' (16avos, solo Sudamericana) → NO otorga puntos (ya se jugó).
  'ronda16' = Octavos · 'cuartos' · 'semis' · 'final'.

Globales:
  Campeón 50 · Subcampeón 50 · orden exacto (ambos) → ×2 (hasta 200).
"""
from __future__ import annotations
from ..base import FaseConfig, ScoringConfig, PartidoScore, GlobalScore, _wdl

# fase.tipo (BD) → FaseConfig. Octavos se guarda como 'ronda16' en clubes.
FASES: dict[str, FaseConfig] = {
    "ronda16": FaseConfig(
        pts_resultado=4, pts_marcador_exacto=8,
        pts_amarillas=3, pts_rojas=3, pts_penales_partido=3,
        pts_sustituciones=3,
        pts_var=0, pts_penales_tanda_por_equipo=0, pts_equipo_clasifica=0,
    ),
    "cuartos": FaseConfig(
        pts_resultado=12, pts_marcador_exacto=24,
        pts_amarillas=5, pts_rojas=5, pts_penales_partido=5,
        pts_sustituciones=5,
        pts_var=0, pts_penales_tanda_por_equipo=0, pts_equipo_clasifica=0,
    ),
    "semis": FaseConfig(
        pts_resultado=30, pts_marcador_exacto=60,
        pts_amarillas=8, pts_rojas=8, pts_penales_partido=8,
        pts_sustituciones=8,
        pts_var=0, pts_penales_tanda_por_equipo=0, pts_equipo_clasifica=0,
    ),
    "final": FaseConfig(
        pts_resultado=75, pts_marcador_exacto=150,
        pts_amarillas=12, pts_rojas=12, pts_penales_partido=12,
        pts_sustituciones=12,
        pts_var=0, pts_penales_tanda_por_equipo=0, pts_equipo_clasifica=0,
    ),
}

# Aliases de nombres de fase que puedan venir de la BD hacia las claves canónicas.
_FASE_ALIAS: dict[str, str] = {
    "octavos": "ronda16", "octavos de final": "ronda16", "8vos": "ronda16",
    "ronda16": "ronda16", "ronda de 16": "ronda16",
    "cuartos": "cuartos", "cuartos de final": "cuartos",
    "semis": "semis", "semifinal": "semis", "semifinales": "semis",
    "final": "final",
}


def _fase_key(fase_tipo: str) -> str | None:
    if not fase_tipo:
        return None
    return _FASE_ALIAS.get(fase_tipo.lower().strip())


# Puntos fijos del cruce (acertar UN solo equipo de la llave siguiente).
CRUCE_BONO_UN_EQUIPO: dict[str, int] = {
    "ronda16": 10, "cuartos": 20, "semis": 40, "final": 0,
}

CONFIG = ScoringConfig(
    nombre="Copa de Clubes — Reglamento BECBUC (Opción C)",
    fases=FASES,
    doble_puntaje_paraguay=False,   # clubes: sin doble Paraguay
    pts_campeon=50,                 # A — campeón
    pts_finalista_por_equipo=50,    # B — subcampeón (finalista no campeón)
)


class CopaClubesScoringEngine:
    """Engine de torneos de clubes a ida y vuelta (reglamento nuevo Opción C)."""

    def get_config(self) -> ScoringConfig:
        return CONFIG

    def score_partido(self, apuesta, partido, fase_tipo, es_paraguay=False, ko_teams_match=True):
        key = _fase_key(fase_tipo)
        cfg = FASES.get(key) if key else None
        score = PartidoScore(
            partido_id=partido["id"], apostador_id=apuesta["apostador_id"],
            fase_tipo=fase_tipo, multiplicador=1, teams_match=ko_teams_match,
        )
        if cfg is None or not ko_teams_match:
            # ronda32 (16avos) u otra fase sin puntaje → cero.
            return score

        pl = apuesta.get("pred_local")
        pv = apuesta.get("pred_visitante")
        rl = partido.get("goles_local")
        rv = partido.get("goles_visitante")
        if None in (pl, pv, rl, rv):
            return score

        # H — Resultado (gana/empata/pierde)
        if _wdl(pl, pv) == _wdl(rl, rv):
            score.pts_resultado = cfg.pts_resultado
            score.pts_marcador_base = 1

        # I — Marcador exacto (acumula con H)
        if pl == rl and pv == rv:
            score.pts_marcador = cfg.pts_marcador_exacto
            score.pts_marcador_base = 3

        # Ítems del partido: SOLO si acierta el número EXACTO y hubo ≥1 evento.
        # (a diferencia del Mundial, el "0-0" NO otorga punto).
        def _evento_exacto(pred, real, pts):
            if real is not None and real > 0 and pred is not None and pred == real:
                return pts
            return 0

        real_amar = partido.get("amarillas")
        real_roja = partido.get("rojas")
        real_pp = partido.get("penales_partido")
        score.pts_amarillas = _evento_exacto(apuesta.get("pred_amarillas"), real_amar, cfg.pts_amarillas)
        score.pts_rojas = _evento_exacto(apuesta.get("pred_rojas"), real_roja, cfg.pts_rojas)
        score.pts_penales_partido = _evento_exacto(apuesta.get("pred_penales_partido"), real_pp, cfg.pts_penales_partido)

        # Sustituciones (reemplazan a VAR): UN total del partido (local+visitante),
        # exacto y ≥1 cambio.
        score.pts_sustituciones = _evento_exacto(
            apuesta.get("pred_sustituciones"), partido.get("sustituciones"),
            cfg.pts_sustituciones,
        )

        # N — minuto del primer gol: el orquestador de clubes decide el ganador y,
        # si acierta, DUPLICA el partido. Acá no se suma nada.

        score.pts_bonus = (
            score.pts_amarillas + score.pts_rojas + score.pts_penales_partido
            + score.pts_sustituciones
        )
        score.pts_total = score.pts_resultado + score.pts_marcador + score.pts_bonus
        return score

    def score_global(self, apuesta_global, torneo_resultados):
        """
        Globales de clubes: A campeón (50), B subcampeón (50).
        Si acierta AMBOS en su lugar exacto (campeón==campeón y finalista2==subcampeón),
        el total de globales se multiplica por 2 (hasta 200).
        """
        score = GlobalScore(apostador_id=apuesta_global.get("apostador_id", 0))

        real_campeon = torneo_resultados.get("campeon_id")
        real_sub = torneo_resultados.get("subcampeon_id")
        # Fallback: derivar subcampeón de los finalistas si no vino explícito.
        if real_sub is None:
            fins = [f for f in (torneo_resultados.get("finalistas_ids") or []) if f is not None]
            if real_campeon is not None and len(fins) == 2:
                real_sub = fins[0] if fins[1] == real_campeon else fins[1]

        pred_campeon = apuesta_global.get("pred_campeon_id")
        # En clubes reutilizamos pred_finalista2_id como "subcampeón pronosticado".
        pred_sub = apuesta_global.get("pred_finalista2_id")
        if pred_sub is None:
            pred_sub = apuesta_global.get("pred_finalista1_id")

        acierto_campeon = (
            pred_campeon is not None and real_campeon is not None
            and pred_campeon == real_campeon
        )
        acierto_sub = (
            pred_sub is not None and real_sub is not None
            and pred_sub == real_sub
        )

        if acierto_campeon:
            score.pts_campeon = CONFIG.pts_campeon          # 50
        if acierto_sub:
            score.pts_finalistas = CONFIG.pts_finalista_por_equipo  # 50

        base = score.pts_campeon + score.pts_finalistas
        # Orden exacto (ambos en su lugar) → ×2
        if acierto_campeon and acierto_sub:
            base *= 2

        score.pts_total = base
        return score
