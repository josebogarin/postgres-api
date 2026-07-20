# -*- coding: utf-8 -*-
"""
test_golden_ranking.py — Test de no-regresion contra el golden master.

Lee el estado ACTUAL de la BD (puntaje_detalle + puntaje_global del torneo 2) y
lo compara, apostador por apostador, contra tests/golden/ranking_torneo2_golden.json.

Flujo de uso en un refactor:
    1) refactor de scoring/ranking
    2) recalcular puntajes (POST /calcular-puntajes/2)
    3) pytest tests/golden  -> debe seguir IDENTICO al golden

Si la BD no esta disponible (Docker apagado), el test se SALTEA (no falla).
"""
import json
import os

import pytest

TID = 2
GOLDEN = os.path.join(os.path.dirname(__file__), "ranking_torneo2_golden.json")
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")


def _cargar_golden():
    if not os.path.exists(GOLDEN):
        pytest.skip("golden aun no generado (correr export_golden.py)")
    with open(GOLDEN, encoding="utf-8") as f:
        return json.load(f)


def _estado_actual_bd():
    """Reproduce la agregacion del golden desde la BD actual. None si no hay BD."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        becbuc = psycopg2.connect(dbname="becbuc", connect_timeout=4, **DB)
        appdb = psycopg2.connect(dbname="app_db", connect_timeout=4, **DB)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"BD no disponible: {e}")
        return None

    bc = becbuc.cursor(cursor_factory=RealDictCursor)
    ac = appdb.cursor(cursor_factory=RealDictCursor)
    ac.execute("SELECT id, username FROM users")
    umap = {r["id"]: r["username"] for r in ac.fetchall()}

    bc.execute(f"""
        SELECT apostador_id,
               COALESCE(SUM(pts_resultado),0) AS h, COALESCE(SUM(pts_marcador),0) AS i,
               COALESCE(SUM(pts_amarillas),0) AS j, COALESCE(SUM(pts_rojas),0) AS k,
               COALESCE(SUM(pts_var),0) AS l, COALESCE(SUM(pts_penales_partido),0) AS m,
               COALESCE(SUM(pts_minuto),0) AS n, COALESCE(SUM(pts_penales_tanda),0) AS o,
               COALESCE(SUM(pts_equipo),0) AS p, COALESCE(SUM(pts_total),0) AS partidos_total
        FROM puntaje_detalle WHERE torneo_id={TID} GROUP BY apostador_id
    """)
    det = {r["apostador_id"]: r for r in bc.fetchall()}
    bc.execute(f"""
        SELECT apostador_id,
               COALESCE(pts_campeon,0) AS a, COALESCE(pts_finalistas,0) AS b,
               COALESCE(pts_goleador,0) AS c, COALESCE(pts_peor_equipo,0) AS d,
               COALESCE(pts_mayor_goleada,0) AS e, COALESCE(pts_etapa_paraguay,0) AS f,
               COALESCE(pts_goles_paraguay,0) AS g, COALESCE(pts_total,0) AS globales_total
        FROM puntaje_global WHERE torneo_id={TID}
    """)
    glob = {r["apostador_id"]: r for r in bc.fetchall()}

    out = {}
    for uid in set(det) | set(glob):
        d = det.get(uid, {}); gg = glob.get(uid, {})
        out[umap.get(uid, f"U{uid}")] = {
            "items": {kk.upper(): int(d.get(kk, 0) or 0) for kk in "hijklmnop"},
            "globales": {kk.upper(): int(gg.get(kk, 0) or 0) for kk in "abcdefg"},
            "total": int(d.get("partidos_total", 0) or 0) + int(gg.get("globales_total", 0) or 0),
        }
    bc.close(); ac.close(); becbuc.close(); appdb.close()
    return out


def test_golden_ranking_sin_regresion():
    golden = _cargar_golden()
    actual = _estado_actual_bd()

    g_ap = golden["apostadores"]
    # Mismos apostadores
    assert set(actual.keys()) == set(g_ap.keys()), (
        f"faltan/sobran apostadores: {set(g_ap) ^ set(actual)}"
    )

    diffs = []
    for alias, g in g_ap.items():
        a = actual[alias]
        if a["items"] != g["items"]:
            diffs.append(f"{alias} items {g['items']} -> {a['items']}")
        if a["globales"] != g["globales"]:
            diffs.append(f"{alias} globales {g['globales']} -> {a['globales']}")
        if a["total"] != g["total"]:
            diffs.append(f"{alias} total {g['total']} -> {a['total']}")
    assert not diffs, "REGRESION vs golden:\n" + "\n".join(diffs)


def test_golden_totales():
    golden = _cargar_golden()
    actual = _estado_actual_bd()
    cobrando_f = sum(1 for a in actual.values() if a["globales"]["F"] == 6)
    assert cobrando_f == golden["totales"]["cobrando_item_F"], (
        f"cobrando item F: golden={golden['totales']['cobrando_item_F']} actual={cobrando_f}"
    )
