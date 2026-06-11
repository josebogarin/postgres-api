"""
copa_mundo_2026.py — Engine oficial Copa del Mundo FIFA 2026.
Implementa el Reglamento BEC BUC 2026 completo.

Tabla de puntajes:
  Concepto      | GR | R32 | R16 | 4tos | Semis | 3P | Final
  H Resultado   |  4 |   6 |   8 |   10 |    12 | 14 |    20
  I Exacto      |  8 |  12 |  16 |   20 |    24 | 28 |    40
  J Amarillas   |  1 |   1 |   1 |    1 |     1 |  1 |     1
  K Rojas       |  1 |   1 |   1 |    1 |     1 |  1 |     1
  L VAR         |  1 |   1 |   1 |    1 |     1 |  1 |     1
  M Pen.partido |  1 |   1 |   1 |    1 |     1 |  1 |     1
  N Min.gol     |  1 |   1 |   1 |    1 |     1 |  1 |     1
  O Pen.tanda   | -- | 2/e | 2/e |  2/e |   2/e |2/e |   2/e
  P Equipo      |  1 |   2 |   4 |    6 |     8 | 10 |    12

Paraguay: DOBLE PUNTAJE en todos los conceptos del partido.
"""
from __future__ import annotations
from ..base import FaseConfig, ScoringConfig, PartidoScore, GlobalScore, _wdl

# ── Tabla de configuración por fase ─────────────────────────────────────────

FASES: dict[str, FaseConfig] = {
    "grupo": FaseConfig(
        pts_resultado=4,
        pts_marcador_exacto=8,
        pts_penales_tanda_por_equipo=0,  # no hay tanda en grupos
        pts_equipo_clasifica=1,
    ),
    "ronda32": FaseConfig(
        pts_resultado=6,
        pts_marcador_exacto=12,
        pts_penales_tanda_por_equipo=2,
        pts_equipo_clasifica=2,
    ),
    "ronda16": FaseConfig(
        pts_resultado=8,
        pts_marcador_exacto=16,
        pts_penales_tanda_por_equipo=2,
        pts_equipo_clasifica=4,
    ),
    "cuartos": FaseConfig(
        pts_resultado=10,
        pts_marcador_exacto=20,
        pts_penales_tanda_por_equipo=2,
        pts_equipo_clasifica=6,
    ),
    "semis": FaseConfig(
        pts_resultado=12,
        pts_marcador_exacto=24,
        pts_penales_tanda_por_equipo=2,
        pts_equipo_clasifica=8,
    ),
    "tercer_puesto": FaseConfig(
        pts_resultado=14,
        pts_marcador_exacto=28,
        pts_penales_tanda_por_equipo=0,  # 3P no tiene tanda en FIFA 2026
        pts_equipo_clasifica=10,
    ),
    "final": FaseConfig(
        pts_resultado=20,
        pts_marcador_exacto=40,
        pts_penales_tanda_por_equipo=2,
        pts_equipo_clasifica=12,
    ),
}

CONFIG = ScoringConfig(
    nombre="Copa del Mundo FIFA 2026 — Reglamento BEC BUC",
    fases=FASES,
    doble_puntaje_paraguay=True,
    # Globales
    pts_campeon=20,
    pts_finalista_por_equipo=10,
    pts_goleador=20,
    pts_peor_equipo=20,
    pts_mayor_goleada_ganador=10,
    pts_mayor_goleada_perdedor=10,
    pts_etapa_paraguay=6,
    pts_goles_paraguay=6,
)


class CopasMundoScoringEngine:
    """Engine oficial para Copa del Mundo FIFA 2026 (Reglamento BEC BUC 2026)."""

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
        cfg = FASES.get(fase_tipo)
        if cfg is None:
            # Fase desconocida: 0 pts
            return PartidoScore(
                partido_id=partido["id"],
                apostador_id=apuesta["apostador_id"],
                fase_tipo=fase_tipo,
                multiplicador=1,
                teams_match=ko_teams_match,
            )

        mult = 2 if (es_paraguay and CONFIG.doble_puntaje_paraguay) else 1

        score = PartidoScore(
            partido_id=partido["id"],
            apostador_id=apuesta["apostador_id"],
            fase_tipo=fase_tipo,
            multiplicador=mult,
            teams_match=ko_teams_match,
        )

        # Sin equipos correctos (KO): 0 en todo
        if not ko_teams_match:
            return score

        pl = apuesta.get("pred_local")
        pv = apuesta.get("pred_visitante")
        rl = partido.get("goles_local")
        rv = partido.get("goles_visitante")

        if None in (pl, pv, rl, rv):
            return score

        # H — Resultado (acertó quién gana/empate)
        if _wdl(pl, pv) == _wdl(rl, rv):
            score.pts_resultado = cfg.pts_resultado * mult
            score.pts_marcador_base = 1  # acierto

        # I — Marcador exacto (incluye resultado, puntaje propio separado)
        if pl == rl and pv == rv:
            score.pts_marcador = cfg.pts_marcador_exacto * mult
            score.pts_marcador_base = 3  # pleno

        # J — Amarillas
        if (apuesta.get("pred_amarillas") is not None
                and partido.get("amarillas") is not None
                and apuesta["pred_amarillas"] == partido["amarillas"]):
            score.pts_amarillas = cfg.pts_amarillas * mult

        # K — Tarjetas rojas
        if (apuesta.get("pred_rojas") is not None
                and partido.get("rojas") is not None
                and apuesta["pred_rojas"] == partido["rojas"]):
            score.pts_rojas = cfg.pts_rojas * mult

        # L — VAR
        if (apuesta.get("pred_var") is not None
                and partido.get("decisiones_var") is not None
                and apuesta["pred_var"] == partido["decisiones_var"]):
            score.pts_var = cfg.pts_var * mult

        # M — Penales sancionados durante el partido (no tanda)
        if (apuesta.get("pred_penales_partido") is not None
                and partido.get("penales_partido") is not None
                and apuesta["pred_penales_partido"] == partido["penales_partido"]):
            score.pts_penales_partido = cfg.pts_penales_partido * mult

        # N — Minuto primer gol: calculado externamente (requiere comparar todos)
        # El calculator suma pts_minuto después de identificar al ganador.

        # O — Penales en tanda (solo si cfg > 0 y hubo tanda real)
        if cfg.pts_penales_tanda_por_equipo > 0:
            tuvo_tanda = partido.get("penales_local") is not None
            if tuvo_tanda:
                for pred_key, real_key in [
                    ("pred_penales_local_tanda", "penales_local"),
                    ("pred_penales_visitante_tanda", "penales_visitante"),
                ]:
                    if (apuesta.get(pred_key) is not None
                            and apuesta[pred_key] == partido[real_key]):
                        score.pts_penales_tanda += cfg.pts_penales_tanda_por_equipo * mult

        # P — Equipo que clasifica
        if (apuesta.get("pred_equipo_clasifica") is not None
                and partido.get("equipo_clasificado_id") is not None
                and apuesta["pred_equipo_clasifica"] == partido["equipo_clasificado_id"]):
            score.pts_equipo = cfg.pts_equipo_clasifica * mult

        # Totales
        score.pts_bonus = (
            score.pts_amarillas + score.pts_rojas + score.pts_var +
            score.pts_penales_partido + score.pts_penales_tanda + score.pts_equipo
            # pts_minuto se suma externamente
        )
        score.pts_total = score.pts_resultado + score.pts_marcador + score.pts_bonus

        return score

    def score_global(self, apuesta_global: dict, torneo_resultados: dict) -> GlobalScore:
        """Pronósticos globales A–G según reglamento BEC BUC 2026."""
        score = GlobalScore(apostador_id=apuesta_global.get("apostador_id", 0))

        # A — Campeón mundial (20 pts)
        if (apuesta_global.get("pred_campeon_id") is not None
                and torneo_resultados.get("campeon_id") is not None
                and apuesta_global["pred_campeon_id"] == torneo_resultados["campeon_id"]):
            score.pts_campeon = CONFIG.pts_campeon

        # B — Finalistas (10 pts por equipo acertado, hasta 20)
        pred_fin = {apuesta_global.get("pred_finalista1_id"),
                    apuesta_global.get("pred_finalista2_id")} - {None}
        real_fin = set(torneo_resultados.get("finalistas_ids") or []) - {None}
        score.pts_finalistas = len(pred_fin & real_fin) * CONFIG.pts_finalista_por_equipo

        # C — Goleador (20 pts, texto libre, case-insensitive)
        pred_gol = (apuesta_global.get("pred_goleador") or "").strip().lower()
        real_gol = (torneo_resultados.get("goleador") or "").strip().lower()
        if pred_gol and real_gol and pred_gol == real_gol:
            score.pts_goleador = CONFIG.pts_goleador

        # D — Peor equipo (20 pts)
        if (apuesta_global.get("pred_peor_equipo_id") is not None
                and torneo_resultados.get("peor_equipo_id") is not None
                and apuesta_global["pred_peor_equipo_id"] == torneo_resultados["peor_equipo_id"]):
            score.pts_peor_equipo = CONFIG.pts_peor_equipo

        # E — Mayor goleada: ganador (10 pts) + perdedor (10 pts) separados
        if (apuesta_global.get("pred_goleada_ganador") is not None
                and torneo_resultados.get("goleada_ganador") is not None
                and apuesta_global["pred_goleada_ganador"] == torneo_resultados["goleada_ganador"]):
            score.pts_mayor_goleada += CONFIG.pts_mayor_goleada_ganador
        if (apuesta_global.get("pred_goleada_perdedor") is not None
                and torneo_resultados.get("goleada_perdedor") is not None
                and apuesta_global["pred_goleada_perdedor"] == torneo_resultados["goleada_perdedor"]):
            score.pts_mayor_goleada += CONFIG.pts_mayor_goleada_perdedor

        # F — Etapa que alcanzó Paraguay (6 pts)
        pred_etapa = apuesta_global.get("pred_etapa_paraguay") or ""
        real_etapa = torneo_resultados.get("etapa_paraguay") or ""
        if pred_etapa and real_etapa and pred_etapa == real_etapa:
            score.pts_etapa_paraguay = CONFIG.pts_etapa_paraguay

        # G — Goles totales Paraguay (6 pts)
        if (apuesta_global.get("pred_goles_paraguay") is not None
                and torneo_resultados.get("goles_paraguay") is not None
                and apuesta_global["pred_goles_paraguay"] == torneo_resultados["goles_paraguay"]):
            score.pts_goles_paraguay = CONFIG.pts_goles_paraguay

        score.pts_total = (score.pts_campeon + score.pts_finalistas + score.pts_goleador
                           + score.pts_peor_equipo + score.pts_mayor_goleada
                           + score.pts_etapa_paraguay + score.pts_goles_paraguay)
        return score
