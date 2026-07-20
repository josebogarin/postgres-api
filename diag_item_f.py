# -*- coding: utf-8 -*-
"""
diag_item_f.py  — VERIFICACION SOLO LECTURA (no modifica nada).

Objetivo: confirmar con datos reales si el item F (Etapa Paraguay, 6 pts) premio
a los apostadores que pusieron OCTAVOS (fase real de eliminacion vs Francia)
o si por error premio a los que pusieron 16avos/r32 (fase vs Alemania).

Reproduce EXACTAMENTE la logica del backend:
  - calculator.py _load_torneo_resultados  (calculo de etapa_paraguay via max_orden)
  - copa_mundo_2026.py _norm_etapa          (normalizacion del pronostico)

Conexion externa psycopg2 (docker-compose): host=localhost user=app_user pass=superpassword
BD torneo = becbuc | BD usuarios = app_db
"""
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

TID = 2  # torneo activo BECBUC

DB = dict(host="localhost", port=5432, user="app_user", password="superpassword")

# ---- copia EXACTA de calculator.py _orden / _inv ---------------------------
_ORDEN = {"final": 7, "tercer_puesto": 6, "semis": 5,
          "cuartos": 4, "ronda16": 3, "ronda32": 2, "grupo": 1}
_INV = {v: k for k, v in _ORDEN.items()}

# ---- copia EXACTA de copa_mundo_2026.py _ETAPA_NORM ------------------------
_ETAPA_NORM = {
    "grupo": "grupo", "ronda32": "ronda32", "ronda16": "ronda16",
    "cuartos": "cuartos", "semis": "semis", "final": "final",
    "tercer_puesto": "final",
    "grupos": "grupo", "fase de grupos": "grupo", "fase grupos": "grupo",
    "group stage": "grupo", "32avos": "ronda32", "32avos de final": "ronda32",
    "16avos": "ronda16", "16avos de final": "ronda16", "octavos": "ronda16",
    "cuartos de final": "cuartos", "quarter": "cuartos", "qf": "cuartos",
    "semifinal": "semis", "semifinales": "semis", "semi": "semis", "sf": "semis",
    "finalista": "final", "tercer puesto": "final", "3er puesto": "final",
    "3rd place": "final",
}
def norm_etapa(v):
    if v is None:
        return ""
    return _ETAPA_NORM.get(str(v).lower().strip(), str(v).lower().strip())


def p(*a):
    print(*a)
    sys.stdout.flush()


def main():
    becbuc = psycopg2.connect(dbname="becbuc", **DB)
    appdb  = psycopg2.connect(dbname="app_db", **DB)
    bc = becbuc.cursor(cursor_factory=RealDictCursor)
    ac = appdb.cursor(cursor_factory=RealDictCursor)

    p("=" * 78)
    p(" DIAG ITEM F — ETAPA PARAGUAY (solo lectura)")
    p("=" * 78)

    # 1) IDs de Paraguay
    bc.execute("SELECT id, nombre FROM equipo WHERE nombre ILIKE '%%paraguay%%'")
    py_rows = bc.fetchall()
    py_ids = [r["id"] for r in py_rows]
    p("\n[1] Equipos Paraguay en BD:", [(r["id"], r["nombre"]) for r in py_rows])
    if not py_ids:
        p("    !! No se encontro Paraguay. Abortando."); return
    ids_sql = ",".join(str(i) for i in py_ids)

    # 2) TODOS los partidos de Paraguay con su fase_tipo
    bc.execute(f"""
        SELECT p.numero_fifa, f.tipo AS fase_tipo, f.nombre AS fase_nombre,
               p.estado, p.goles_local, p.goles_visitante,
               p.equipo_local_id, p.equipo_visitante_id,
               el.nombre AS local, ev.nombre AS visit
        FROM partido p
        JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.torneo_id = {TID}
          AND (p.equipo_local_id IN ({ids_sql}) OR p.equipo_visitante_id IN ({ids_sql}))
        ORDER BY p.numero_fifa NULLS LAST
    """)
    matches = bc.fetchall()
    p("\n[2] Partidos de Paraguay (todos):")
    p("    NumFIFA | fase_tipo   | estado      | marcador | rival / partido")
    for m in matches:
        rival = m["visit"] if m["equipo_local_id"] in py_ids else m["local"]
        gl, gv = m["goles_local"], m["goles_visitante"]
        marc = f"{gl}-{gv}" if gl is not None else " - "
        p(f"    {str(m['numero_fifa']):>7} | {str(m['fase_tipo']):<11} | "
          f"{str(m['estado']):<11} | {marc:^8} | {m['local']} vs {m['visit']}  (rival={rival})")

    # 3) Replicar el filtro y el max_orden del calculator
    p("\n[3] Calculo de etapa_paraguay (replica de calculator.py):")
    p("    Filtro del algoritmo: estado='finalizado' AND numero_fifa IS NOT NULL")
    considerados = [m for m in matches
                    if m["estado"] == "finalizado" and m["numero_fifa"] is not None]
    p("    Partidos que ENTRAN al calculo:")
    for m in considerados:
        orden = _ORDEN.get(m["fase_tipo"], 0)
        p(f"      Num {m['numero_fifa']}: fase_tipo={m['fase_tipo']!r} -> orden={orden}")
    excluidos = [m for m in matches if m not in considerados]
    if excluidos:
        p("    Partidos EXCLUIDOS del calculo (no finalizado o sin numero_fifa):")
        for m in excluidos:
            p(f"      Num {m['numero_fifa']}: fase_tipo={m['fase_tipo']!r} estado={m['estado']!r}")
    if considerados:
        max_orden = max(_ORDEN.get(m["fase_tipo"], 0) for m in considerados)
        etapa_calc = _INV.get(max_orden)
    else:
        max_orden, etapa_calc = 0, None
    p(f"\n    >>> max_orden = {max_orden}")
    p(f"    >>> etapa_paraguay CALCULADA = {etapa_calc!r}  (norm={norm_etapa(etapa_calc)!r})")
    p(f"    >>> Esperado segun realidad  = 'ronda16' (Octavos, Paraguay 0-1 Francia)")
    if etapa_calc == "ronda32":
        p("    *** CONFIRMADO: el sistema quedo en ronda32 (16avos) en vez de ronda16 (octavos).")
    elif etapa_calc == "ronda16":
        p("    *** El sistema tiene ronda16 (octavos) — el desfase estaria en el pronostico.")

    # 4) Distribucion de pred_etapa_paraguay
    p("\n[4] Distribucion pred_etapa_paraguay en apuesta_global (torneo %d):" % TID)
    bc.execute(f"""
        SELECT pred_etapa_paraguay AS pe, COUNT(*) AS n
        FROM apuesta_global WHERE torneo_id={TID}
        GROUP BY pred_etapa_paraguay ORDER BY n DESC
    """)
    dist = bc.fetchall()
    p("    valor_guardado | norm_etapa | == etapa_calc? | count")
    for d in dist:
        nz = norm_etapa(d["pe"])
        match = "SI-cobra" if (nz and nz == norm_etapa(etapa_calc)) else "no"
        p(f"    {str(d['pe']):<14} | {nz:<10} | {match:<14} | {d['n']}")

    # 5) Mapa apostador_id -> username (app_db)
    ac.execute("SELECT id, username, COALESCE(nombre,'') AS nombre FROM users")
    umap = {r["id"]: r for r in ac.fetchall()}

    # 6) Por apostador: pred + pts_etapa_paraguay
    bc.execute(f"""
        SELECT ag.apostador_id, ag.pred_etapa_paraguay AS pe,
               pg.pts_etapa_paraguay AS pts
        FROM apuesta_global ag
        LEFT JOIN puntaje_global pg
          ON pg.torneo_id=ag.torneo_id AND pg.apostador_id=ag.apostador_id
        WHERE ag.torneo_id={TID}
        ORDER BY pg.pts_etapa_paraguay DESC NULLS LAST, ag.apostador_id
    """)
    rows = bc.fetchall()

    p("\n[5] cherem vs decanita (foco del reporte):")
    for row in rows:
        u = umap.get(row["apostador_id"], {})
        uname = (u.get("username") or "").lower()
        if uname in ("cherem", "decanita"):
            p(f"    {u.get('username'):<10} (id={row['apostador_id']}) "
              f"pred={row['pe']!r} norm={norm_etapa(row['pe'])!r} "
              f"pts_F={row['pts']}  nombre={u.get('nombre')!r}")

    # 7) Quienes cobraron los 6 pts vs quienes pusieron octavos
    p("\n[6] TODOS los que cobraron pts_etapa_paraguay > 0:")
    cobraron = [r for r in rows if (r["pts"] or 0) > 0]
    for r in cobraron:
        u = umap.get(r["apostador_id"], {})
        p(f"    {u.get('username','?'):<12} pred={r['pe']!r} norm={norm_etapa(r['pe'])!r} pts={r['pts']}")
    p(f"    total que cobraron F: {len(cobraron)}")

    # 8) Quienes pusieron 'octavos'/'8vos' (intencion octavos) — cobraron o no
    p("\n[7] Apostadores cuya intencion fue OCTAVOS (pred contiene 8/octavos):")
    def es_octavos(v):
        s = (v or "").lower()
        return "octav" in s or s in ("8vos", "8vo", "r16", "ronda16")
    oct_rows = [r for r in rows if es_octavos(r["pe"])]
    if not oct_rows:
        p("    (ninguno con texto de octavos en pred_etapa_paraguay)")
    for r in oct_rows:
        u = umap.get(r["apostador_id"], {})
        p(f"    {u.get('username','?'):<12} pred={r['pe']!r} pts={r['pts']}  "
          f"{'COBRO' if (r['pts'] or 0)>0 else 'NO COBRO'}")

    p("\n[8] Apostadores cuya intencion fue 16avos/r32 (pred 16avos/ronda32):")
    def es_16(v):
        s = (v or "").lower()
        return s in ("16avos", "16avos de final", "ronda32", "32avos") or "16av" in s
    r16_rows = [r for r in rows if es_16(r["pe"])]
    for r in r16_rows:
        u = umap.get(r["apostador_id"], {})
        p(f"    {u.get('username','?'):<12} pred={r['pe']!r} pts={r['pts']}  "
          f"{'COBRO' if (r['pts'] or 0)>0 else 'NO COBRO'}")

    p("\n" + "=" * 78)
    p(" RESUMEN")
    p("=" * 78)
    p(f"  etapa_paraguay calculada por el sistema : {etapa_calc!r}")
    p(f"  etapa real (Paraguay eliminado)         : 'ronda16' (Octavos vs Francia)")
    p(f"  cobraron F (6 pts)                      : {len(cobraron)} apostadores")
    p(f"  con intencion octavos                   : {len(oct_rows)} (ver cuales COBRO/NO)")
    p(f"  con intencion 16avos/r32                : {len(r16_rows)} (ver cuales COBRO/NO)")
    p("=" * 78)

    bc.close(); ac.close(); becbuc.close(); appdb.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        p("ERROR:", e)
        traceback.print_exc()
