# -*- coding: utf-8 -*-
"""
test_scoring_engine.py — Tests unitarios PUROS del motor de scoring (sin BD).
Bloquean las reglas del reglamento BEC BUC 2026, incluido el fix del item F.
Si un refactor cambia el comportamiento del engine, estos tests fallan.
"""
from app.services.scoring.engines.copa_mundo_2026 import CopasMundoScoringEngine

ENG = CopasMundoScoringEngine()


def _apuesta(pl, pv, **kw):
    d = dict(
        apostador_id=1, pred_local=pl, pred_visitante=pv,
        pred_amarillas=None, pred_rojas=None, pred_var=None,
        pred_penales_partido=None, pred_penales_local_tanda=None,
        pred_penales_visitante_tanda=None, pred_equipo_clasifica=None,
    )
    d.update(kw)
    return d


def _partido(gl, gv, **kw):
    # Por defecto los bonus reales != 0 para que NO matcheen con preds vacias (0),
    # y asi aislar H/I salvo que el test los setee.
    d = dict(
        id=1, goles_local=gl, goles_visitante=gv,
        amarillas=9, rojas=9, decisiones_var=9, penales_partido=9,
        penales_local=None, penales_visitante=None,
        equipo_local_id=10, equipo_visitante_id=20, equipo_clasificado_id=None,
    )
    d.update(kw)
    return d


# ── H / I por fase ────────────────────────────────────────────────────────────
def test_grupo_marcador_exacto():
    s = ENG.score_partido(_apuesta(2, 1), _partido(2, 1), "grupo")
    assert s.pts_resultado == 4      # H grupos
    assert s.pts_marcador == 8       # I grupos
    assert s.pts_marcador_base == 3  # pleno
    assert s.pts_total == 12         # bonus 0 (preds vacias no matchean)


def test_grupo_resultado_sin_exacto():
    s = ENG.score_partido(_apuesta(2, 0), _partido(3, 1), "grupo")  # ambos gana local
    assert s.pts_resultado == 4
    assert s.pts_marcador == 0
    assert s.pts_marcador_base == 1


def test_grupo_fallo():
    s = ENG.score_partido(_apuesta(0, 2), _partido(1, 0), "grupo")  # predijo V, gano L
    assert s.pts_resultado == 0
    assert s.pts_marcador == 0
    assert s.pts_marcador_base == 0


def test_final_marcador_exacto():
    s = ENG.score_partido(_apuesta(1, 0), _partido(1, 0), "final")
    assert s.pts_resultado == 20     # H final
    assert s.pts_marcador == 40      # I final
    assert s.pts_total == 60


def test_paraguay_doble_puntaje():
    s = ENG.score_partido(_apuesta(2, 1), _partido(2, 1), "grupo", es_paraguay=True)
    assert s.multiplicador == 2
    assert s.pts_resultado == 8      # 4 x2
    assert s.pts_marcador == 16      # 8 x2


# ── Items bonus ───────────────────────────────────────────────────────────────
def test_item_j_amarillas_exacto():
    ap = _apuesta(0, 0, pred_amarillas=3)          # marcador fallara (E vs L)
    pt = _partido(1, 0, amarillas=3)               # amarillas coincide
    s = ENG.score_partido(ap, pt, "grupo")
    assert s.pts_amarillas == 1
    assert s.pts_resultado == 0                    # aislado: solo J suma
    assert s.pts_bonus == 1


def test_item_p_no_se_duplica_para_paraguay():
    # KO ronda32, victoria local predicha, clasifica el local -> P = 2 (NO x2)
    ap = _apuesta(2, 0)
    pt = _partido(1, 0, equipo_clasificado_id=10)  # local clasifica
    s = ENG.score_partido(ap, pt, "ronda32", es_paraguay=True)
    assert s.pts_equipo == 2                       # ronda32=2, sin multiplicar por Paraguay


# ── Item F (Etapa Paraguay) — bloquea el fix de nomenclatura ──────────────────
def _f(pred):
    ag = {"apostador_id": 1, "pred_etapa_paraguay": pred}
    tr = {"etapa_paraguay": "ronda16"}             # Paraguay eliminado en octavos
    return ENG.score_global(ag, tr).pts_etapa_paraguay


def test_item_f_8vos_cobra():
    assert _f("8vos") == 6            # octavos por Excel import -> cobra


def test_item_f_octavos_cobra():
    assert _f("octavos") == 6


def test_item_f_ronda16_cobra():
    assert _f("ronda16") == 6


def test_item_f_16avos_no_cobra():
    assert _f("16avos") == 0          # 16avos = R32 (Alemania) -> NO cobra


def test_item_f_ronda32_no_cobra():
    assert _f("ronda32") == 0


def test_item_f_cuartos_no_cobra():
    assert _f("cuartos") == 0


# ── Globales A / B ────────────────────────────────────────────────────────────
def test_global_campeon():
    ag = {"apostador_id": 1, "pred_campeon_id": 7}
    tr = {"campeon_id": 7}
    assert ENG.score_global(ag, tr).pts_campeon == 20


def test_global_finalistas_cuenta_campeon():
    # Comportamiento actual: el campeon (=finalista1) cuenta como finalista acertado (+10)
    ag = {"apostador_id": 1, "pred_finalista1_id": 1, "pred_finalista2_id": 2}
    tr = {"finalistas_ids": [1, 3]}   # finalistas reales: 1 y 3
    assert ENG.score_global(ag, tr).pts_finalistas == 10
