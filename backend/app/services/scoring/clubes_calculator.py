# -*- coding: utf-8 -*-
"""
clubes_calculator.py — Orquestador de puntajes para torneos de CLUBES
(Libertadores / Sudamericana), reglamento nuevo (Opción C).

Diferencias con el Mundial:
  - Se juega por SERIES a ida y vuelta (la final es partido único).
  - No hay 3er puesto. Los 16avos (ronda32) NO otorgan puntos.
  - Sustituciones (un total) reemplazan a VAR → se guardan en pts_var.
  - Multiplicadores de serie: comodín ×3, definición por penales ×2,
    minuto del primer gol ×2 (por pierna), y el "cruce" (×2 si acertás los
    dos que se cruzan en la ronda siguiente, o bono fijo si acertás uno).

Persistencia: puntaje_detalle (misma tabla que el Mundial). Mapa de columnas:
  H→pts_resultado · I→pts_marcador · amarillas→pts_amarillas · rojas→pts_rojas ·
  sustituciones→pts_var · penales_juego→pts_penales_partido ·
  bono de cruce→pts_equipo · (pts_minuto y pts_penales_tanda quedan en 0: el
  minuto y la tanda actúan como MULTIPLICADORES, no como puntos aparte).

Todo el módulo es defensivo: cualquier error se acumula en 'warnings' y no
rompe el proceso. El scoring del Mundial no se toca.
"""
from __future__ import annotations
from collections import defaultdict
from sqlalchemy import text

from .engines.copa_clubes import (
    CopaClubesScoringEngine, _fase_key, CRUCE_BONO_UN_EQUIPO,
)

# Fases que otorgan puntos en clubes (16avos = ronda32 NO puntúa).
FASES_PUNTABLES = ("ronda16", "cuartos", "semis", "final")
# Rondas donde aplica el bono de cruce (la final no tiene ronda siguiente).
FASES_CON_CRUCE = ("ronda16", "cuartos", "semis")


async def _load_partido_cols(db):
    """Devuelve el set de columnas presentes en 'partido' (para tolerar esquemas)."""
    try:
        r = await db.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='partido'"))
        return {row[0] for row in r}
    except Exception:
        return set()


async def calcular_clubes(db, torneo_id: int) -> dict:
    """Calcula y persiste los puntajes de un torneo de clubes. Idempotente."""
    engine = CopaClubesScoringEngine()
    warnings: list[str] = []

    pcols = await _load_partido_cols(db)
    sust_col = "p.sustituciones" if "sustituciones" in pcols else "NULL::int"

    # ── 1) Fases KO ordenadas ────────────────────────────────────────────────
    rf = await db.execute(text("""
        SELECT id, nombre, tipo, orden
        FROM fase
        WHERE torneo_id = :tid AND tipo IN ('ronda32','ronda16','cuartos','semis','final')
        ORDER BY orden, id
    """), {"tid": torneo_id})
    fases = [dict(x) for x in rf.mappings()]
    if not fases:
        return {"ok": False, "error": "El torneo no tiene fases KO de clubes.", "series": 0}

    # ── 2) Partidos + apuestas + comodín, por fase ───────────────────────────
    # acc[(partido_id, aid)] = columnas de puntaje acumuladas
    acc: dict[tuple[int, int], dict] = {}
    # series_by_fase[fase_id] = lista de series (cada una con legs + meta)
    series_by_fase: dict[int, list[dict]] = {}

    for f in fases:
        fase_key = _fase_key(f["tipo"])
        puntable = f["tipo"] in FASES_PUNTABLES and fase_key is not None

        rp = await db.execute(text(f"""
            SELECT p.id, p.estado, p.fecha, p.fase_id,
                   p.goles_local AS gl, p.goles_visitante AS gv,
                   p.penales_local AS pen_l, p.penales_visitante AS pen_v,
                   p.amarillas, p.rojas, COALESCE(p.penales_partido,0) AS penales_partido,
                   p.minuto_primer_gol, {sust_col} AS sustituciones,
                   p.equipo_local_id AS local_id, p.equipo_visitante_id AS visit_id,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre,
                   p.equipo_clasificado_id AS clasif_id
            FROM partido p
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.fase_id = :fid
            ORDER BY p.fecha NULLS LAST, p.id
        """), {"fid": f["id"]})
        legs = [dict(x) for x in rp.mappings()]

        # Agrupar en series por par de equipos reales (mismo criterio que bracket-clubes)
        def _real(row, side):
            tid = row[side + "_id"]; nom = row[side + "_nombre"]
            return bool(tid) and bool(nom) and str(nom).strip().lower() not in ("tbd", "por definir")

        def _key(r):
            ids = []
            if _real(r, "local"): ids.append(r["local_id"])
            if _real(r, "visit"): ids.append(r["visit_id"])
            return frozenset(ids) if ids else None

        grupos: dict = {}
        orden_keys = []
        for r in legs:
            k = _key(r)
            if k is None:
                continue
            if k not in grupos:
                grupos[k] = []
                orden_keys.append(k)
            grupos[k].append(r)

        fase_series = []
        for k in orden_keys:
            g = sorted(grupos[k], key=lambda x: (x["fecha"].timestamp() if x["fecha"] else 1e18, x["id"]))
            # teamA/teamB desde la pierna con equipos reales
            tA = tB = None
            for lg in g:
                if _real(lg, "local") and _real(lg, "visit"):
                    tA, tB = lg["local_id"], lg["visit_id"]
                    break
            fase_series.append({
                "fase_id": f["id"], "fase_tipo": f["tipo"], "fase_nombre": f["nombre"],
                "fase_key": fase_key, "puntable": puntable,
                "teamA": tA, "teamB": tB, "legs": g,
            })
        series_by_fase[f["id"]] = fase_series

        if not puntable:
            continue  # 16avos: agrupa pero no puntúa

        # Cargar apuestas de estos partidos (con comodín)
        pids = [lg["id"] for lg in legs if lg["estado"] == "finalizado"]
        if not pids:
            continue
        ids_sql = ",".join(str(i) for i in pids)
        ra = await db.execute(text(f"""
            SELECT a.apostador_id, a.partido_id,
                   a.pred_local, a.pred_visitante,
                   a.pred_amarillas, a.pred_rojas,
                   COALESCE(a.pred_penales_partido,0) AS pred_penales_partido,
                   a.pred_sustituciones, a.pred_minuto_gol,
                   a.pred_penales_local_tanda, a.pred_penales_visitante_tanda,
                   COALESCE(a.pred_comodin, FALSE) AS pred_comodin
            FROM apuesta a
            WHERE a.partido_id IN ({ids_sql})
        """), {})
        apuestas = [dict(x) for x in ra.mappings()]
        ap_by_leg: dict[tuple[int, int], dict] = {}
        for ap in apuestas:
            ap_by_leg[(ap["partido_id"], ap["apostador_id"])] = ap

        # Ganadores del minuto por partido (más cercano al real, empate = todos)
        minuto_win: dict[int, set[int]] = {}
        legmap = {lg["id"]: lg for lg in legs}
        preds_by_pid: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for ap in apuestas:
            if ap.get("pred_minuto_gol") is not None:
                preds_by_pid[ap["partido_id"]].append((ap["apostador_id"], ap["pred_minuto_gol"]))
        for pid, preds in preds_by_pid.items():
            real_min = (legmap.get(pid) or {}).get("minuto_primer_gol")
            if real_min is None or real_min == 99:
                continue
            dmin = min(abs(pr - real_min) for _, pr in preds)
            minuto_win[pid] = {aid for aid, pr in preds if abs(pr - real_min) == dmin}

        # ── Base por pierna (con minuto ×2) ──────────────────────────────────
        for s in fase_series:
            for lg in s["legs"]:
                if lg["estado"] != "finalizado" or lg["gl"] is None or lg["gv"] is None:
                    continue
                for (pid, aid), ap in list(ap_by_leg.items()):
                    if pid != lg["id"]:
                        continue
                    sc = engine.score_partido(ap, lg, f["tipo"], es_paraguay=False, ko_teams_match=True)
                    mmin = 2 if aid in minuto_win.get(lg["id"], set()) else 1
                    acc[(lg["id"], aid)] = {
                        "fase_id": f["id"], "fase_tipo": f["tipo"], "fase_nombre": f["nombre"],
                        "gl": lg["gl"], "gv": lg["gv"],
                        "pl": ap.get("pred_local"), "pv": ap.get("pred_visitante"),
                        "base_marcador_base": sc.pts_marcador_base,
                        "h": sc.pts_resultado * mmin,
                        "i": sc.pts_marcador * mmin,
                        "j": sc.pts_amarillas * mmin,
                        "k": sc.pts_rojas * mmin,
                        "sub": sc.pts_sustituciones * mmin,
                        "m": sc.pts_penales_partido * mmin,
                        "eq": 0,               # bono de cruce (se llena luego)
                        "mult_min": mmin,
                    }

    # ── 3) Multiplicadores de serie: comodín ×3 y tanda ×2 ───────────────────
    def _serie_aids(s) -> set[int]:
        out = set()
        for lg in s["legs"]:
            for (pid, aid) in acc:
                if pid == lg["id"]:
                    out.add(aid)
        return out

    def _pred_winner(s, aid):
        """Ganador de la serie según los marcadores pronosticados por el apostador."""
        A, B = s["teamA"], s["teamB"]
        if A is None or B is None:
            return None, False  # (winner_id, tie)
        aggA = aggB = 0; complete = True
        for lg in s["legs"]:
            ap = None
            for (pid, a2) in acc:
                if pid == lg["id"] and a2 == aid:
                    ap = acc[(pid, a2)]; break
            if not ap or ap["pl"] is None or ap["pv"] is None:
                complete = False; break
            if lg["local_id"] == A:
                aggA += ap["pl"]; aggB += ap["pv"]
            else:
                aggB += ap["pl"]; aggA += ap["pv"]
        if not complete:
            return None, False
        if aggA > aggB: return A, False
        if aggB > aggA: return B, False
        return None, True  # empate global pronosticado

    def _real_winner(s):
        """Ganador real de la serie: clasif_id de alguna pierna, o por goles agregados."""
        for lg in s["legs"]:
            if lg.get("clasif_id"):
                return lg["clasif_id"]
        A, B = s["teamA"], s["teamB"]
        if A is None or B is None:
            return None
        gA = gB = 0; jugados = 0
        for lg in s["legs"]:
            if lg["estado"] != "finalizado" or lg["gl"] is None:
                continue
            jugados += 1
            if lg["local_id"] == A: gA += lg["gl"]; gB += lg["gv"]
            else: gB += lg["gl"]; gA += lg["gv"]
        if jugados == 0:
            return None
        if gA > gB: return A
        if gB > gA: return B
        return None  # empate → penales (no resuelto acá)

    def _serie_tied_real(s):
        """La serie real terminó empatada en el global (se definió por penales)."""
        A, B = s["teamA"], s["teamB"]
        if A is None or B is None:
            return False
        gA = gB = 0; jugados = 0; n = 0
        for lg in s["legs"]:
            n += 1
            if lg["estado"] != "finalizado" or lg["gl"] is None:
                continue
            jugados += 1
            if lg["local_id"] == A: gA += lg["gl"]; gB += lg["gv"]
            else: gB += lg["gl"]; gA += lg["gv"]
        return jugados == n and n > 0 and gA == gB

    def _mult_serie(s, aid, factor):
        for lg in s["legs"]:
            key = (lg["id"], aid)
            if key in acc:
                for c in ("h", "i", "j", "k", "sub", "m"):
                    acc[key][c] *= factor

    # Comodín ×3 y tanda ×2 se aplican con una query fresca (evita cargar todo en memoria).
    await _aplicar_comodin_y_tanda(db, torneo_id, series_by_fase, acc, _serie_aids,
                                   _pred_winner, _serie_tied_real, _mult_serie, warnings)

    # ── 4) Cruce: por pares de series consecutivas de cada ronda ─────────────
    for fid, fase_series in series_by_fase.items():
        if not fase_series:
            continue
        ftipo = fase_series[0]["fase_tipo"]
        if ftipo not in FASES_CON_CRUCE:
            continue
        bono = CRUCE_BONO_UN_EQUIPO.get(_fase_key(ftipo) or "", 0)
        completas = [s for s in fase_series if s.get("puntable")]
        for i in range(0, len(completas) - 1, 2):
            s1, s2 = completas[i], completas[i + 1]
            rw1, rw2 = _real_winner(s1), _real_winner(s2)
            for aid in (_serie_aids(s1) | _serie_aids(s2)):
                pw1, _ = _pred_winner(s1, aid)
                pw2, _ = _pred_winner(s2, aid)
                ok1 = pw1 is not None and rw1 is not None and pw1 == rw1
                ok2 = pw2 is not None and rw2 is not None and pw2 == rw2
                if ok1 and ok2:
                    _mult_serie(s1, aid, 2)
                    _mult_serie(s2, aid, 2)
                elif ok1 ^ ok2:
                    # bono fijo en la última pierna finalizada de la serie acertada
                    s_ok = s1 if ok1 else s2
                    last = None
                    for lg in s_ok["legs"]:
                        if (lg["id"], aid) in acc:
                            last = lg["id"]
                    if last is not None:
                        acc[(last, aid)]["eq"] += bono

    # ── 5) Persistir en puntaje_detalle ──────────────────────────────────────
    # Borra solo las fases KO puntables de este torneo (idempotente).
    await db.execute(text("""
        DELETE FROM puntaje_detalle
        WHERE torneo_id = :tid AND partido_id IN (
            SELECT p.id FROM partido p JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND f.tipo IN ('ronda16','cuartos','semis','final'))
    """), {"tid": torneo_id})

    plenos = aciertos = fallos = 0
    for (pid, aid), c in acc.items():
        bonus = c["j"] + c["k"] + c["sub"] + c["m"] + c["eq"]
        total = c["h"] + c["i"] + bonus
        base = c["base_marcador_base"]
        if base == 3: plenos += 1
        elif base == 1: aciertos += 1
        else: fallos += 1
        await db.execute(text("""
            INSERT INTO puntaje_detalle
              (torneo_id, fase_id, fase_tipo, fase_nombre, partido_id, apostador_id,
               multiplicador, pred_local, pred_visitante, real_local, real_visitante,
               pts_marcador_base, pts_marcador,
               pred_minuto, real_minuto, gano_minuto, pts_minuto,
               pred_amarillas, real_amarillas, pts_amarillas,
               pred_var, real_var, pts_var,
               teams_match, pred_penales, real_penales, pts_penales,
               pts_bonus, pts_total,
               pts_resultado, pts_rojas, pts_penales_partido, pts_penales_tanda, pts_equipo)
            VALUES
              (:tid, :fid, :ftipo, :fnom, :pid, :uid,
               1, :pl, :pv, :rl, :rv,
               :base, :i,
               NULL, NULL, FALSE, 0,
               NULL, NULL, :j,
               NULL, NULL, :sub,
               TRUE, NULL, NULL, 0,
               :bonus, :total,
               :h, :k, :m, 0, :eq)
            ON CONFLICT (torneo_id, partido_id, apostador_id) DO UPDATE SET
               fase_id=EXCLUDED.fase_id, fase_tipo=EXCLUDED.fase_tipo,
               fase_nombre=EXCLUDED.fase_nombre,
               pred_local=EXCLUDED.pred_local, pred_visitante=EXCLUDED.pred_visitante,
               real_local=EXCLUDED.real_local, real_visitante=EXCLUDED.real_visitante,
               pts_marcador_base=EXCLUDED.pts_marcador_base, pts_marcador=EXCLUDED.pts_marcador,
               pts_amarillas=EXCLUDED.pts_amarillas, pts_var=EXCLUDED.pts_var,
               pts_bonus=EXCLUDED.pts_bonus, pts_total=EXCLUDED.pts_total,
               pts_resultado=EXCLUDED.pts_resultado, pts_rojas=EXCLUDED.pts_rojas,
               pts_penales_partido=EXCLUDED.pts_penales_partido,
               pts_penales_tanda=0, pts_equipo=EXCLUDED.pts_equipo
        """), {
            "tid": torneo_id, "fid": c["fase_id"], "ftipo": c["fase_tipo"], "fnom": c["fase_nombre"],
            "pid": pid, "uid": aid, "pl": c["pl"], "pv": c["pv"], "rl": c["gl"], "rv": c["gv"],
            "base": base, "i": c["i"], "j": c["j"], "sub": c["sub"],
            "bonus": bonus, "total": total, "h": c["h"], "k": c["k"], "m": c["m"], "eq": c["eq"],
        })

    await db.commit()

    # ── 6) Globales (campeón / subcampeón) ───────────────────────────────────
    globales = await _calcular_globales_clubes(db, torneo_id, engine, series_by_fase, warnings)

    return {
        "ok": True, "series": sum(len(v) for v in series_by_fase.values()),
        "filas": len(acc), "plenos": plenos, "aciertos": aciertos, "fallos": fallos,
        "globales": globales, "warnings": warnings,
    }


async def _aplicar_comodin_y_tanda(db, torneo_id, series_by_fase, acc, serie_aids,
                                   pred_winner, serie_tied_real, mult_serie, warnings):
    """Aplica comodín ×3 y definición por penales ×2, con una query fresca de apuestas."""
    # Mapa (partido_id, aid) -> apuesta (comodín + tanda pronosticada)
    pids = [pid for (pid, _aid) in acc]
    if not pids:
        return
    ids_sql = ",".join(str(i) for i in set(pids))
    r = await db.execute(text(f"""
        SELECT partido_id, apostador_id,
               COALESCE(pred_comodin, FALSE) AS pred_comodin,
               pred_penales_local_tanda AS ptl, pred_penales_visitante_tanda AS ptv
        FROM apuesta WHERE partido_id IN ({ids_sql})
    """), {})
    apinfo = {(x["partido_id"], x["apostador_id"]): x for x in r.mappings()}

    for fid, fase_series in series_by_fase.items():
        for s in fase_series:
            if not s.get("puntable"):
                continue
            A, B = s["teamA"], s["teamB"]
            for aid in serie_aids(s):
                # Comodín: si lo marcó en cualquier pierna de la serie
                comodin = any(
                    (apinfo.get((lg["id"], aid)) or {}).get("pred_comodin")
                    for lg in s["legs"]
                )
                if comodin:
                    mult_serie(s, aid, 3)
                # Tanda ×2: serie realmente empatada + apostador pronostica empate global
                # + acierta la tanda en la pierna decisiva.
                if serie_tied_real(s):
                    _pw, pred_tie = pred_winner(s, aid)
                    if pred_tie:
                        # pierna decisiva = última finalizada
                        dec = None
                        for lg in s["legs"]:
                            if lg["estado"] == "finalizado":
                                dec = lg
                        if dec and dec.get("pen_l") is not None and dec.get("pen_v") is not None:
                            ap = apinfo.get((dec["id"], aid)) or {}
                            if ap.get("ptl") == dec["pen_l"] and ap.get("ptv") == dec["pen_v"]:
                                mult_serie(s, aid, 2)


async def _calcular_globales_clubes(db, torneo_id, engine, series_by_fase, warnings) -> int:
    """Campeón (50) / subcampeón (50), ×2 si acierta el orden. Persiste puntaje_global."""
    # Determinar campeón y subcampeón desde la final
    campeon_id = subcampeon_id = None
    for fid, fase_series in series_by_fase.items():
        for s in fase_series:
            if s["fase_tipo"] != "final":
                continue
            A, B = s["teamA"], s["teamB"]
            if A is None or B is None:
                continue
            gA = gB = 0; jugados = 0; n = 0
            for lg in s["legs"]:
                n += 1
                if lg["estado"] != "finalizado" or lg["gl"] is None:
                    continue
                jugados += 1
                if lg["local_id"] == A: gA += lg["gl"]; gB += lg["gv"]
                else: gB += lg["gl"]; gA += lg["gv"]
                if lg.get("clasif_id"):
                    campeon_id = lg["clasif_id"]
            if jugados == n and n > 0:
                if campeon_id is None:
                    campeon_id = A if gA > gB else (B if gB > gA else None)
                if campeon_id is not None:
                    subcampeon_id = B if campeon_id == A else A
    if campeon_id is None:
        return 0  # final no jugada

    tr = {"campeon_id": campeon_id, "subcampeon_id": subcampeon_id,
          "finalistas_ids": [campeon_id, subcampeon_id]}

    r = await db.execute(text("SELECT * FROM apuesta_global WHERE torneo_id=:tid"), {"tid": torneo_id})
    globs = [dict(x) for x in r.mappings()]
    if not globs:
        return 0
    await db.execute(text("DELETE FROM puntaje_global WHERE torneo_id=:tid"), {"tid": torneo_id})
    n = 0
    for ag in globs:
        sc = engine.score_global(ag, tr)
        await db.execute(text("""
            INSERT INTO puntaje_global
              (torneo_id, apostador_id, pts_campeon, pts_finalistas, pts_goleador,
               pts_peor_equipo, pts_mayor_goleada, pts_etapa_paraguay, pts_goles_paraguay,
               pts_total, calculado_at)
            VALUES (:tid, :uid, :pc, :pf, 0, 0, 0, 0, 0, :total, NOW())
            ON CONFLICT (torneo_id, apostador_id) DO UPDATE SET
               pts_campeon=EXCLUDED.pts_campeon, pts_finalistas=EXCLUDED.pts_finalistas,
               pts_total=EXCLUDED.pts_total, calculado_at=NOW()
        """), {"tid": torneo_id, "uid": ag["apostador_id"],
               "pc": sc.pts_campeon, "pf": sc.pts_finalistas, "total": sc.pts_total})
        n += 1
    await db.commit()
    return n
