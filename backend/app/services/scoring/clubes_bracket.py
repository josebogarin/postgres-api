# -*- coding: utf-8 -*-
"""
clubes_bracket.py — Avance automático del bracket de CLUBES (ida/vuelta).

Cuando una llave KO está finalizada (ambas piernas), calcula el ganador
(goles agregados; empate → penales de la vuelta) y lo propaga al slot de la
ronda siguiente:
  ronda32 (16avos) → reemplaza el placeholder "Gan. X/Y" del octavo (match por tokens).
  ronda16 (octavos) → reemplaza "Gan. O{k}" en cuartos (posicional).
  cuartos           → reemplaza "Gan. C{k}" en semis.
  semis             → reemplaza "Gan. S{k}" en la final.

Topología POSICIONAL: la llave k (1-based, orden por p.id) alimenta "Gan. {L}{k}"
de la ronda siguiente (creada por crear_arbol_ko_clubes.py con {2j+1}/{2j+2}).
Idempotente. Solo escribe cuando el ganador está definido y el slot es placeholder.
"""
from __future__ import annotations
import re, unicodedata
from sqlalchemy import text

_TBD = ("tbd", "por definir")


def _norm(x):
    if not x:
        return ""
    return unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower().strip()


def _es_tbd(n):
    return n is None or _norm(n) in _TBD


async def _llaves_full(db, tid, tipo):
    """Series (ida/vuelta) de una fase, agrupadas por par de equipos reales, orden p.id."""
    r = await db.execute(text("""
        SELECT p.id, p.equipo_local_id AS lid, p.equipo_visitante_id AS vid,
               el.nombre AS ln, ev.nombre AS vn,
               p.goles_local AS gl, p.goles_visitante AS gv,
               p.penales_local AS pl, p.penales_visitante AS pv, p.estado AS est
        FROM partido p JOIN fase f ON f.id = p.fase_id
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE f.torneo_id = :tid AND f.tipo = :tipo
        ORDER BY p.id
    """), {"tid": tid, "tipo": tipo})
    rows = [dict(x) for x in r.mappings()]
    grupos, orden = {}, []
    for r_ in rows:
        ids = [i for i in ((r_["lid"], r_["ln"]), (r_["vid"], r_["vn"])) if i[0] and not _es_tbd(i[1])]
        key = frozenset(i[0] for i in ids)
        if not key:
            continue
        if key not in grupos:
            grupos[key] = []
            orden.append(key)
        grupos[key].append(r_)
    return [grupos[k] for k in orden]


def _ganador(legs):
    """(id, nombre) del ganador de la serie, o None si no está decidida."""
    reales = set()
    for r in legs:
        for i, n in ((r["lid"], r["ln"]), (r["vid"], r["vn"])):
            if i and not _es_tbd(n):
                reales.add((i, n))
    if len(reales) != 2:
        return None
    if not all(r["est"] == "finalizado" and r["gl"] is not None and r["gv"] is not None for r in legs):
        return None
    (a, an), (b, bn) = list(reales)
    agg = {a: 0, b: 0}
    for r in legs:
        if r["lid"] in agg: agg[r["lid"]] += r["gl"]
        if r["vid"] in agg: agg[r["vid"]] += r["gv"]
    if agg[a] > agg[b]: return (a, an)
    if agg[b] > agg[a]: return (b, bn)
    # empate global → penales de la pierna que los tenga (normalmente la vuelta)
    for r in legs:
        if r["pl"] is not None and r["pv"] is not None and r["pl"] != r["pv"]:
            return (r["lid"], r["ln"]) if r["pl"] > r["pv"] else (r["vid"], r["vn"])
    return None


async def _reemplazar(db, tid, fase_tipo, ph_nombre, winner_id):
    """Reemplaza el equipo placeholder (por nombre) por winner_id en la fase dada."""
    r = await db.execute(text("SELECT id FROM equipo WHERE nombre = :n LIMIT 1"), {"n": ph_nombre})
    row = r.first()
    if not row:
        return 0
    ph_id = row[0]
    if ph_id == winner_id:
        return 0
    r2 = await db.execute(text("""
        SELECT p.id, p.equipo_local_id, p.equipo_visitante_id
        FROM partido p JOIN fase f ON f.id = p.fase_id
        WHERE f.torneo_id = :tid AND f.tipo = :ft
          AND (p.equipo_local_id = :ph OR p.equipo_visitante_id = :ph)
    """), {"tid": tid, "ft": fase_tipo, "ph": ph_id})
    n = 0
    for pid, lid, vid in r2.fetchall():
        if lid == ph_id:
            await db.execute(text("UPDATE partido SET equipo_local_id = :w WHERE id = :pid"),
                             {"w": winner_id, "pid": pid})
        else:
            await db.execute(text("UPDATE partido SET equipo_visitante_id = :w WHERE id = :pid"),
                             {"w": winner_id, "pid": pid})
        n += 1
    return n


def _toks(ph):
    t = re.split(r"[/ ]+", _norm(ph).replace("gan.", "").replace("gan ", ""))
    return [x for x in t if len(x) >= 3]


async def cerrar_fases_completas(db, torneo_id: int) -> list:
    """Bloquea (cierra) las fases KO cuyos partidos estan TODOS finalizados.
    Una fase bloqueada ya no admite edicion de apuestas (check en live-guardar)."""
    r = await db.execute(text("""
        UPDATE fase SET bloqueada = TRUE
        WHERE torneo_id = :tid
          AND tipo IN ('ronda32','ronda16','cuartos','semis','tercer_puesto','final')
          AND COALESCE(bloqueada, FALSE) = FALSE
          AND (SELECT COUNT(*) FROM partido p WHERE p.fase_id = fase.id) > 0
          AND (SELECT COUNT(*) FROM partido p WHERE p.fase_id = fase.id AND p.estado <> 'finalizado') = 0
        RETURNING nombre, tipo
    """), {"tid": torneo_id})
    return [f"{row[1]}:{row[0]}" for row in r.fetchall()]


async def avanzar_bracket_clubes(db, torneo_id: int) -> dict:
    """Propaga ganadores de clubes octavos→cuartos→semis→final (+ 16avos→octavos).
    Escribe directo (idempotente). Devuelve {'propagaciones': [...], 'n': N}."""
    prop = []

    # 1) 16avos → octavos (match por tokens con 'Gan. X/Y')
    r32 = await _llaves_full(db, torneo_id, "ronda32")
    if r32:
        rp = await db.execute(text("""
            SELECT DISTINCT e.id, e.nombre FROM equipo e
            JOIN partido p ON (p.equipo_local_id = e.id OR p.equipo_visitante_id = e.id)
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND f.tipo = 'ronda16' AND lower(e.nombre) LIKE 'gan%'
        """), {"tid": torneo_id})
        phs = [(row[0], row[1]) for row in rp.fetchall()]
        for legs in r32:
            w = _ganador(legs)
            if not w:
                continue
            reales = set()
            for r in legs:
                for i, n in ((r["lid"], r["ln"]), (r["vid"], r["vn"])):
                    if i and not _es_tbd(n):
                        reales.add(_norm(n).split()[0])
            for _pid_e, pn in phs:
                pt = _toks(pn)
                if any(any(t.startswith(rt) or rt.startswith(t) for rt in reales) for t in pt):
                    c = await _reemplazar(db, torneo_id, "ronda16", pn, w[0])
                    if c:
                        prop.append(f"16avos {sorted(reales)} -> {w[1]} (reemplaza '{pn}' en octavos, {c})")
                    break

    # 2) posicional: octavos→cuartos (O), cuartos→semis (C), semis→final (S)
    for tipo, ab, sig in (("ronda16", "O", "cuartos"), ("cuartos", "C", "semis"), ("semis", "S", "final")):
        llaves = await _llaves_full(db, torneo_id, tipo)
        for k, legs in enumerate(llaves, start=1):
            w = _ganador(legs)
            if not w:
                continue
            c = await _reemplazar(db, torneo_id, sig, f"Gan. {ab}{k}", w[0])
            if c:
                prop.append(f"{tipo} llave {k} -> {w[1]} (reemplaza 'Gan. {ab}{k}' en {sig}, {c})")

    cerradas = await cerrar_fases_completas(db, torneo_id)
    await db.commit()
    return {"propagaciones": prop, "n": len(prop), "fases_cerradas": cerradas}
