# -*- coding: utf-8 -*-
"""
export_golden.py — Congela el "golden master" del torneo cerrado (torneo_id=2).

Lee la BD post-fix del item F y vuelca, por apostador:
  - items de partido H-P (suma de puntaje_detalle)
  - globales A-G (puntaje_global)
  - total
y agregados a nivel torneo, a  tests/golden/ranking_torneo2_golden.json.

SOLO LECTURA. Se ejecuta UNA vez para congelar la referencia; si el JSON ya
existe no lo regenera (usar --force para reescribir).

Uso:
    python tests/golden/export_golden.py [--force]
"""
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

TID = 2
DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")
OUT = os.path.join(os.path.dirname(__file__), "ranking_torneo2_golden.json")


def build_golden():
    becbuc = psycopg2.connect(dbname="becbuc", **DB)
    appdb = psycopg2.connect(dbname="app_db", **DB)
    bc = becbuc.cursor(cursor_factory=RealDictCursor)
    ac = appdb.cursor(cursor_factory=RealDictCursor)

    ac.execute("SELECT id, username FROM users")
    umap = {r["id"]: r["username"] for r in ac.fetchall()}

    # Items de partido H-P por apostador (suma sobre todos los partidos)
    bc.execute(f"""
        SELECT apostador_id,
               COALESCE(SUM(pts_resultado),0)       AS h,
               COALESCE(SUM(pts_marcador),0)        AS i,
               COALESCE(SUM(pts_amarillas),0)       AS j,
               COALESCE(SUM(pts_rojas),0)           AS k,
               COALESCE(SUM(pts_var),0)             AS l,
               COALESCE(SUM(pts_penales_partido),0) AS m,
               COALESCE(SUM(pts_minuto),0)          AS n,
               COALESCE(SUM(pts_penales_tanda),0)   AS o,
               COALESCE(SUM(pts_equipo),0)          AS p,
               COALESCE(SUM(pts_total),0)           AS partidos_total,
               COUNT(*) FILTER (WHERE pts_marcador > 0) AS plenos,
               COUNT(*) FILTER (WHERE pts_resultado > 0 AND pts_marcador = 0) AS aciertos
        FROM puntaje_detalle
        WHERE torneo_id = {TID}
        GROUP BY apostador_id
    """)
    det = {r["apostador_id"]: r for r in bc.fetchall()}

    # Globales A-G por apostador
    bc.execute(f"""
        SELECT apostador_id,
               COALESCE(pts_campeon,0)         AS a,
               COALESCE(pts_finalistas,0)      AS b,
               COALESCE(pts_goleador,0)        AS c,
               COALESCE(pts_peor_equipo,0)     AS d,
               COALESCE(pts_mayor_goleada,0)   AS e,
               COALESCE(pts_etapa_paraguay,0)  AS f,
               COALESCE(pts_goles_paraguay,0)  AS g,
               COALESCE(pts_total,0)           AS globales_total
        FROM puntaje_global
        WHERE torneo_id = {TID}
    """)
    glob = {r["apostador_id"]: r for r in bc.fetchall()}

    apostadores = {}
    ids = set(det) | set(glob)
    for uid in ids:
        d = det.get(uid, {})
        gg = glob.get(uid, {})
        items = {kk.upper(): int(d.get(kk, 0) or 0) for kk in
                 ("h", "i", "j", "k", "l", "m", "n", "o", "p")}
        globales = {kk.upper(): int(gg.get(kk, 0) or 0) for kk in
                    ("a", "b", "c", "d", "e", "f", "g")}
        partidos_total = int(d.get("partidos_total", 0) or 0)
        globales_total = int(gg.get("globales_total", 0) or 0)
        apostadores[umap.get(uid, f"U{uid}")] = {
            "apostador_id": uid,
            "items": items,
            "globales": globales,
            "partidos_total": partidos_total,
            "globales_total": globales_total,
            "total": partidos_total + globales_total,
            "plenos": int(d.get("plenos", 0) or 0),
            "aciertos": int(d.get("aciertos", 0) or 0),
        }

    # Agregados a nivel torneo
    tot_plenos = sum(a["plenos"] for a in apostadores.values())
    tot_aciertos = sum(a["aciertos"] for a in apostadores.values())
    cobrando_f = sum(1 for a in apostadores.values() if a["globales"]["F"] == 6)

    golden = {
        "torneo_id": TID,
        "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "descripcion": "Golden master del torneo cerrado (post-fix item F). Referencia de no-regresion.",
        "totales": {
            "apostadores": len(apostadores),
            "plenos": tot_plenos,
            "aciertos": tot_aciertos,
            "cobrando_item_F": cobrando_f,
        },
        "apostadores": dict(sorted(apostadores.items())),
    }

    bc.close(); ac.close(); becbuc.close(); appdb.close()
    return golden


def main():
    force = "--force" in sys.argv
    if os.path.exists(OUT) and not force:
        print(f"[golden] ya existe: {OUT}  (usar --force para reescribir). No se regenera.")
        return
    golden = build_golden()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(golden, f, ensure_ascii=False, indent=2)
    print(f"[golden] escrito: {OUT}")
    print(f"[golden] apostadores={golden['totales']['apostadores']} "
          f"plenos={golden['totales']['plenos']} aciertos={golden['totales']['aciertos']} "
          f"cobrando_F={golden['totales']['cobrando_item_F']}")


if __name__ == "__main__":
    main()
