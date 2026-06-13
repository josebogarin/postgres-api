"""
calculator.py — Orquestador ScoringCalculator.
Encapsula: cargar datos, puntuar via engine, persistir en BD.
El endpoint calcular_puntajes llama:
    result = await ScoringCalculator(db).calculate(torneo_id, engine)
"""
from __future__ import annotations
from collections import defaultdict
from sqlalchemy import text
from .base import ScoringEngine, PartidoScore, _wdl


class ScoringCalculator:
    def __init__(self, db):
        self.db = db

    # ── Punto de entrada ──────────────────────────────────────────────────────

    async def calculate(self, torneo_id: int, engine: ScoringEngine) -> dict | None:
        """
        Calcula y persiste todos los puntajes del torneo usando el engine dado.
        Devuelve dict resumen {plenos, aciertos, fallos, por_fase}
        o None si no hay partidos finalizados.
        """
        db = self.db

        # 1) Cargar partidos finalizados (con columnas v2)
        partidos = await self._load_partidos(db, torneo_id)
        if not partidos:
            return None

        # 2) Cargar apuestas (con columnas v2)
        apuestas = await self._load_apuestas(db, torneo_id)

        # 3) IDs de equipos Paraguay (para doble puntaje)
        paraguay_ids = await self._get_paraguay_ids(db)

        # 4) Mapa KO pid↔num
        ko_maps = await self._build_ko_maps(db, torneo_id)
        pid2num_ko = ko_maps.get("pid2num", {})

        # 5) Bracket predicho por apostador (para teams_match en KO)
        apostadores_set = {ap["apostador_id"] for ap in apuestas}
        pred_bracket_by_uid = await self._build_pred_brackets(db, torneo_id, apostadores_set)

        # 6) Ganadores del minuto por partido
        minuto_bonus_ids = self._compute_minuto_winners(apuestas, partidos)

        # 7) Limpiar puntaje_detalle previo (recalculo idempotente)
        await db.execute(
            text("DELETE FROM puntaje_detalle WHERE torneo_id=:tid"),
            {"tid": torneo_id},
        )

        # Limpiar ítems de partido de puntaje_item (los globales se borran en calculate_global)
        try:
            await db.execute(
                text("DELETE FROM puntaje_item WHERE torneo_id=:tid AND partido_id IS NOT NULL"),
                {"tid": torneo_id},
            )
        except Exception:
            pass  # tabla puede no existir aún si no se ejecutó la migración

        # 8) Puntuar cada apuesta
        plenos = aciertos = fallos = 0
        por_fase: dict[str, dict] = {}

        for ap in apuestas:
            p = partidos.get(ap["partido_id"])
            if not p:
                continue

            tipo = p["fase_tipo"]

            # teams_match: en grupos siempre True; en KO compara bracket predicho vs real
            teams_match = self._check_teams_match(
                ap["partido_id"], ap["apostador_id"], tipo,
                pid2num_ko, pred_bracket_by_uid, partidos,
            )

            # Doble puntaje si alguno de los equipos del partido es Paraguay
            es_paraguay = bool(
                paraguay_ids
                & {p.get("equipo_local_id"), p.get("equipo_visitante_id")}
            )

            score = engine.score_partido(
                apuesta=ap,
                partido=p,
                fase_tipo=tipo,
                es_paraguay=es_paraguay,
                ko_teams_match=teams_match,
            )

            # Añadir pts_minuto si ganó ese ítem
            if ap["id"] in minuto_bonus_ids and teams_match:
                cfg = engine.get_config().fases.get(tipo)
                if cfg:
                    mult = 2 if (es_paraguay and engine.get_config().doble_puntaje_paraguay) else 1
                    score.pts_minuto = cfg.pts_minuto_gol * mult
                    score.gano_minuto = True
                    score.pts_bonus += score.pts_minuto
                    score.pts_total += score.pts_minuto

            # Contadores resumen
            base = score.pts_marcador_base
            if base == 3:    plenos  += 1
            elif base == 1:  aciertos += 1
            else:            fallos   += 1

            f = por_fase.setdefault(tipo, {"marcador": 0, "bonus": 0, "total": 0, "apuestas": 0})
            f["marcador"]  += score.pts_resultado + score.pts_marcador
            f["bonus"]     += score.pts_bonus
            f["total"]     += score.pts_total
            f["apuestas"]  += 1

            # Persistir en puntaje_detalle (tabla legacy, mantiene compatibilidad)
            await self._persist_score(db, torneo_id, score, ap, p)

            # Persistir en puntaje_item (auditoría granular: una fila por ítem)
            try:
                await self._persist_items(db, torneo_id, score, ap, p)
            except Exception:
                pass  # no bloquear si la tabla aún no existe

        return {"plenos": plenos, "aciertos": aciertos, "fallos": fallos, "por_fase": por_fase}

    # ── Pronósticos globales A-G ─────────────────────────────────────────────

    async def calculate_global(self, torneo_id: int, engine) -> dict:
        """
        Calcula y persiste puntajes globales A-G.
        Solo se ejecuta cuando hay un campeón definido (torneo terminado).
        Si no hay campeón, limpia puntaje_global y retorna procesadas=0.
        Devuelve dict {procesadas, torneo_resultados, sin_campeon}.
        """
        db = self.db

        torneo_resultados = await self._load_torneo_resultados(db, torneo_id)

        # ── REGLA: globales solo al terminar el torneo (cuando hay campeón) ──
        if not torneo_resultados.get("campeon_id"):
            # Sin campeón → borrar cualquier puntaje_global previo y salir
            await db.execute(
                text("DELETE FROM puntaje_global WHERE torneo_id = :tid"),
                {"tid": torneo_id},
            )
            try:
                await db.execute(
                    text("DELETE FROM puntaje_item WHERE torneo_id=:tid AND partido_id IS NULL"),
                    {"tid": torneo_id},
                )
            except Exception:
                pass
            return {"procesadas": 0, "torneo_resultados": torneo_resultados, "sin_campeon": True}

        r = await db.execute(
            text("SELECT * FROM apuesta_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )
        apuestas_globales = [dict(row) for row in r.mappings()]
        if not apuestas_globales:
            return {"procesadas": 0, "torneo_resultados": torneo_resultados}

        await db.execute(
            text("DELETE FROM puntaje_global WHERE torneo_id = :tid"),
            {"tid": torneo_id},
        )

        # Limpiar ítems globales de puntaje_item
        try:
            await db.execute(
                text("DELETE FROM puntaje_item WHERE torneo_id=:tid AND partido_id IS NULL"),
                {"tid": torneo_id},
            )
        except Exception:
            pass  # tabla puede no existir aún

        for ag in apuestas_globales:
            score = engine.score_global(ag, torneo_resultados)

            # Persistir en puntaje_item (auditoría granular A-G)
            try:
                await self._persist_global_items(db, torneo_id, ag, score, torneo_resultados)
            except Exception:
                pass  # no bloquear si la tabla aún no existe

            await db.execute(
                text("""
                    INSERT INTO puntaje_global
                      (torneo_id, apostador_id,
                       pts_campeon, pts_finalistas, pts_goleador,
                       pts_peor_equipo, pts_mayor_goleada,
                       pts_etapa_paraguay, pts_goles_paraguay, pts_total,
                       calculado_at)
                    VALUES
                      (:tid, :uid,
                       :pc, :pf, :pg, :ppe, :pmg, :pep, :pgp, :total,
                       NOW())
                    ON CONFLICT (torneo_id, apostador_id) DO UPDATE SET
                       pts_campeon=EXCLUDED.pts_campeon,
                       pts_finalistas=EXCLUDED.pts_finalistas,
                       pts_goleador=EXCLUDED.pts_goleador,
                       pts_peor_equipo=EXCLUDED.pts_peor_equipo,
                       pts_mayor_goleada=EXCLUDED.pts_mayor_goleada,
                       pts_etapa_paraguay=EXCLUDED.pts_etapa_paraguay,
                       pts_goles_paraguay=EXCLUDED.pts_goles_paraguay,
                       pts_total=EXCLUDED.pts_total,
                       calculado_at=NOW()
                """),
                {
                    "tid": torneo_id, "uid": ag["apostador_id"],
                    "pc":  score.pts_campeon,    "pf":  score.pts_finalistas,
                    "pg":  score.pts_goleador,   "ppe": score.pts_peor_equipo,
                    "pmg": score.pts_mayor_goleada, "pep": score.pts_etapa_paraguay,
                    "pgp": score.pts_goles_paraguay, "total": score.pts_total,
                },
            )

        return {"procesadas": len(apuestas_globales), "torneo_resultados": torneo_resultados}

    async def _load_torneo_resultados(self, db, torneo_id: int) -> dict:
        """
        Resultados reales del torneo para puntuar pronósticos A-G.
          A/B: auto (partido final + equipo_clasificado_id)
          C:   admin-set (torneo.resultado_goleador)
          D:   admin-set (torneo.resultado_peor_equipo_id)
          E:   auto (max diferencia de goles)
          F/G: auto (partidos de Paraguay)
        """
        result: dict = {}

        # A + B — Campeón y finalistas (partido final)
        try:
            r = await db.execute(
                text("""
                    SELECT p.equipo_local_id, p.equipo_visitante_id,
                           p.equipo_clasificado_id
                    FROM partido p
                    JOIN fase f ON f.id = p.fase_id
                    WHERE p.torneo_id = :tid AND f.tipo = 'final'
                      AND p.estado = 'finalizado'
                    LIMIT 1
                """),
                {"tid": torneo_id},
            )
            final = r.mappings().first()
            if final:
                result["campeon_id"]    = final["equipo_clasificado_id"]
                result["finalistas_ids"] = [final["equipo_local_id"],
                                             final["equipo_visitante_id"]]
        except Exception:
            pass

        # C — Goleador (admin-set: torneo.resultado_goleador)
        try:
            r = await db.execute(
                text("SELECT resultado_goleador FROM torneo WHERE id = :tid"),
                {"tid": torneo_id},
            )
            row = r.mappings().first()
            result["goleador"] = (row or {}).get("resultado_goleador")
        except Exception:
            result["goleador"] = None  # columna aún no existe

        # D — Peor equipo (admin-set: torneo.resultado_peor_equipo_id)
        try:
            r = await db.execute(
                text("SELECT resultado_peor_equipo_id FROM torneo WHERE id = :tid"),
                {"tid": torneo_id},
            )
            row = r.mappings().first()
            result["peor_equipo_id"] = (row or {}).get("resultado_peor_equipo_id")
        except Exception:
            result["peor_equipo_id"] = None

        # E — Mayor goleada del torneo
        try:
            r = await db.execute(
                text("""
                    SELECT goles_local, goles_visitante,
                           ABS(goles_local - goles_visitante) AS diff
                    FROM partido
                    WHERE torneo_id = :tid AND estado = 'finalizado'
                      AND goles_local IS NOT NULL AND goles_visitante IS NOT NULL
                    ORDER BY diff DESC, goles_local + goles_visitante DESC
                    LIMIT 1
                """),
                {"tid": torneo_id},
            )
            goleada = r.mappings().first()
            if goleada:
                gl, gv = goleada["goles_local"], goleada["goles_visitante"]
                result["goleada_ganador"]  = max(gl, gv)
                result["goleada_perdedor"] = min(gl, gv)
        except Exception:
            pass

        # F + G — Etapa y goles de Paraguay
        # NOTA: asyncpg no soporta listas Python en ANY(:param) → usar IN con IDs inlineados.
        try:
            paraguay_ids = await self._get_paraguay_ids(db)
            if paraguay_ids:
                _orden = {"final": 7, "tercer_puesto": 6, "semis": 5,
                          "cuartos": 4, "ronda16": 3, "ronda32": 2, "grupo": 1}
                _inv   = {v: k for k, v in _orden.items()}
                ids_sql = ",".join(str(i) for i in paraguay_ids)
                r = await db.execute(
                    text(f"""
                        SELECT f.tipo AS fase_tipo,
                               CASE WHEN p.equipo_local_id    IN ({ids_sql}) THEN p.goles_local
                                    WHEN p.equipo_visitante_id IN ({ids_sql}) THEN p.goles_visitante
                                    ELSE 0 END AS goles_py
                        FROM partido p
                        JOIN fase f ON f.id = p.fase_id
                        WHERE p.torneo_id = :tid AND p.estado = 'finalizado'
                          AND (p.equipo_local_id    IN ({ids_sql})
                               OR  p.equipo_visitante_id IN ({ids_sql}))
                    """),
                    {"tid": torneo_id},
                )
                rows = r.mappings().all()
                if rows:
                    result["goles_paraguay"] = sum((row["goles_py"] or 0) for row in rows)
                    max_orden = max(_orden.get(row["fase_tipo"], 0) for row in rows)
                    result["etapa_paraguay"] = _inv.get(max_orden)
        except Exception:
            pass

        return result

    # ── Carga de datos ────────────────────────────────────────────────────────

    async def _load_partidos(self, db, torneo_id: int) -> dict[int, dict]:
        r = await db.execute(
            text("""
                SELECT p.id, p.fase_id, f.tipo AS fase_tipo, f.nombre AS fase_nombre,
                       p.equipo_local_id, p.equipo_visitante_id,
                       p.goles_local, p.goles_visitante,
                       p.penales_local, p.penales_visitante,
                       p.minuto_primer_gol, p.amarillas, p.decisiones_var,
                       p.rojas, p.penales_partido, p.equipo_clasificado_id,
                       p.fecha,
                       el.nombre AS local_nombre,
                       ev.nombre AS visit_nombre
                FROM partido p
                JOIN fase f ON f.id = p.fase_id
                LEFT JOIN equipo el ON el.id = p.equipo_local_id
                LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE p.torneo_id = :tid AND p.estado = 'finalizado'
                  AND p.goles_local IS NOT NULL AND p.goles_visitante IS NOT NULL
            """),
            {"tid": torneo_id},
        )
        return {row["id"]: dict(row) for row in r.mappings()}

    async def _load_apuestas(self, db, torneo_id: int) -> list[dict]:
        # Usamos JOIN en vez de ANY(:lista) — asyncpg+text() no acepta listas Python.
        r = await db.execute(
            text("""
                SELECT a.id, a.apostador_id, a.partido_id,
                       a.pred_local, a.pred_visitante,
                       a.pred_minuto_gol, a.pred_amarillas, a.pred_var,
                       a.pred_penales,
                       a.pred_rojas,
                       a.pred_penales_local_tanda,
                       a.pred_penales_visitante_tanda,
                       a.pred_penales_partido,
                       a.pred_equipo_clasifica
                FROM apuesta a
                JOIN partido p ON p.id = a.partido_id
                WHERE p.torneo_id = :tid
                  AND p.estado = 'finalizado'
                  AND p.goles_local IS NOT NULL
                  AND p.goles_visitante IS NOT NULL
            """),
            {"tid": torneo_id},
        )
        return [dict(row) for row in r.mappings()]

    async def _get_paraguay_ids(self, db) -> set[int]:
        # NUNCA llamar db.rollback() aquí: destruiría transacciones en curso.
        # nombre_es puede no existir en equipo → usar solo nombre.
        try:
            r = await db.execute(
                text("SELECT id FROM equipo WHERE nombre ILIKE '%paraguay%'")
            )
            return {row[0] for row in r}
        except Exception:
            return set()

    async def _build_ko_maps(self, db, torneo_id: int) -> dict:
        try:
            from app.services import ko_scoring
            return await ko_scoring.build_num_maps(db, torneo_id)
        except Exception:
            return {"pid2num": {}, "num2pid": {}}

    async def _build_pred_brackets(
        self, db, torneo_id: int, apostadores_set: set[int]
    ) -> dict[int, dict[int, dict]]:
        try:
            from app.services.torneo_service import (
                simular_standings_usuario,
                seleccionar_mejores_terceros,
                armar_ronda32,
            )
            from app.services.bracket_service import propagar_ko_usuario
        except ImportError:
            return {}

        result: dict[int, dict] = {}
        for uid in apostadores_set:
            try:
                pred_st  = await simular_standings_usuario(db, uid, torneo_id)
                pred_mej, _ = seleccionar_mejores_terceros(pred_st)
                r32_b    = armar_ronda32(pred_st, pred_mej)
                ko_b     = await propagar_ko_usuario(db, uid, torneo_id, r32_b)
                result[uid] = {m["num"]: m for m in ko_b}
            except Exception:
                result[uid] = {}
        return result

    # ── Lógica auxiliar ──────────────────────────────────────────────────────

    def _compute_minuto_winners(
        self, apuestas: list[dict], partidos: dict[int, dict]
    ) -> set[int]:
        """Devuelve el conjunto de apuesta_ids que ganan el bonus de minuto_gol."""
        minuto_preds: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for ap in apuestas:
            if ap.get("pred_minuto_gol") is not None:
                minuto_preds[ap["partido_id"]].append((ap["id"], ap["pred_minuto_gol"]))

        winners: set[int] = set()
        for pid, preds in minuto_preds.items():
            real_min = (partidos.get(pid) or {}).get("minuto_primer_gol")
            if real_min is None:
                continue
            min_dist = min(abs(pred - real_min) for _, pred in preds)
            for aid, pred in preds:
                if abs(pred - real_min) == min_dist:
                    winners.add(aid)
        return winners

    def _check_teams_match(
        self,
        partido_id: int,
        uid: int,
        tipo: str,
        pid2num_ko: dict,
        pred_bracket_by_uid: dict,
        partidos: dict,
    ) -> bool:
        if tipo == "grupo":
            return True
        num = pid2num_ko.get(partido_id)
        if num is None:
            return False
        pred_m = (pred_bracket_by_uid.get(uid) or {}).get(num)
        if not pred_m:
            return False
        p = partidos[partido_id]
        return (
            pred_m.get("local_id") == p.get("equipo_local_id")
            and pred_m.get("visit_id") == p.get("equipo_visitante_id")
        )

    # ── Auditoría granular por ítem ───────────────────────────────────────────

    def _build_partido_items(
        self, score: PartidoScore, ap: dict, p: dict
    ) -> list[dict]:
        """
        Devuelve una lista de dicts con (item, resultado, apuesta, puntaje) para
        cada concepto de partido: H, I, J, K, L, M, N, O, P.
        categoria = 'partido' para todos.
        """
        rl = p.get("goles_local")
        rv = p.get("goles_visitante")
        pl = ap.get("pred_local")
        pv = ap.get("pred_visitante")

        def _s(v) -> str | None:
            return str(v) if v is not None else None

        items = [
            # H — Resultado (L=local gana, E=empate, V=visitante gana)
            {
                "item": "H",
                "resultado": _wdl(rl, rv) if (rl is not None and rv is not None) else None,
                "apuesta":   _wdl(pl, pv) if (pl is not None and pv is not None) else None,
                "puntaje":   score.pts_resultado,
            },
            # I — Marcador exacto
            {
                "item": "I",
                "resultado": f"{rl}-{rv}" if (rl is not None and rv is not None) else None,
                "apuesta":   f"{pl}-{pv}" if (pl is not None and pv is not None) else None,
                "puntaje":   score.pts_marcador,
            },
            # J — Amarillas
            {
                "item": "J",
                "resultado": _s(p.get("amarillas")),
                "apuesta":   _s(ap.get("pred_amarillas")),
                "puntaje":   score.pts_amarillas,
            },
            # K — Rojas
            {
                "item": "K",
                "resultado": _s(p.get("rojas")),
                "apuesta":   _s(ap.get("pred_rojas")),
                "puntaje":   score.pts_rojas,
            },
            # L — VAR
            {
                "item": "L",
                "resultado": _s(p.get("decisiones_var")),
                "apuesta":   _s(ap.get("pred_var")),
                "puntaje":   score.pts_var,
            },
            # M — Penales sancionados durante el partido
            {
                "item": "M",
                "resultado": _s(p.get("penales_partido")),
                "apuesta":   _s(ap.get("pred_penales_partido")),
                "puntaje":   score.pts_penales_partido,
            },
            # N — Minuto primer gol (pts_minuto ya fue asignado externamente)
            {
                "item": "N",
                "resultado": _s(p.get("minuto_primer_gol")),
                "apuesta":   _s(ap.get("pred_minuto_gol")),
                "puntaje":   score.pts_minuto,
            },
            # O — Penales en tanda (formato "local-visitante")
            {
                "item": "O",
                "resultado": (
                    f"{p['penales_local']}-{p['penales_visitante']}"
                    if p.get("penales_local") is not None else None
                ),
                "apuesta": (
                    f"{ap['pred_penales_local_tanda']}-{ap['pred_penales_visitante_tanda']}"
                    if ap.get("pred_penales_local_tanda") is not None else None
                ),
                "puntaje": score.pts_penales_tanda,
            },
            # P — Equipo que clasifica (equipo_id como texto)
            {
                "item": "P",
                "resultado": _s(p.get("equipo_clasificado_id")),
                "apuesta":   _s(ap.get("pred_equipo_clasifica")),
                "puntaje":   score.pts_equipo,
            },
        ]
        return items

    async def _persist_items(
        self, db, torneo_id: int, score: PartidoScore, ap: dict, p: dict
    ) -> None:
        """Upsert una fila en puntaje_item por cada item H-P del partido."""
        items = self._build_partido_items(score, ap, p)
        for it in items:
            await db.execute(
                text("""
                    INSERT INTO puntaje_item
                      (torneo_id, partido_id, apostador_id, categoria, item,
                       fase_tipo, fase_nombre, fecha_partido,
                       local_nombre, visit_nombre,
                       resultado, apuesta, puntaje, multiplicador, updated_at)
                    VALUES
                      (:tid, :pid, :uid, 'partido', :item,
                       :ftipo, :fnom, :fecha,
                       :local_n, :visit_n,
                       :resultado, :apuesta, :puntaje, :mult, NOW())
                    ON CONFLICT (partido_id, apostador_id, item)
                    WHERE partido_id IS NOT NULL
                    DO UPDATE SET
                      torneo_id     = EXCLUDED.torneo_id,
                      fase_tipo     = EXCLUDED.fase_tipo,
                      fase_nombre   = EXCLUDED.fase_nombre,
                      fecha_partido = EXCLUDED.fecha_partido,
                      local_nombre  = EXCLUDED.local_nombre,
                      visit_nombre  = EXCLUDED.visit_nombre,
                      resultado     = EXCLUDED.resultado,
                      apuesta       = EXCLUDED.apuesta,
                      puntaje       = EXCLUDED.puntaje,
                      multiplicador = EXCLUDED.multiplicador,
                      updated_at    = NOW()
                """),
                {
                    "tid":       torneo_id,
                    "pid":       score.partido_id,
                    "uid":       score.apostador_id,
                    "item":      it["item"],
                    "ftipo":     p["fase_tipo"],
                    "fnom":      p["fase_nombre"],
                    "fecha":     p.get("fecha"),
                    "local_n":   p.get("local_nombre"),
                    "visit_n":   p.get("visit_nombre"),
                    "resultado": it["resultado"],
                    "apuesta":   it["apuesta"],
                    "puntaje":   it["puntaje"],
                    "mult":      score.multiplicador,
                },
            )

    def _build_global_items(self, ag: dict, score, torneo_resultados: dict) -> list:
        """Devuelve lista (item, resultado, apuesta, puntaje) para globales A-G."""
        def _s(v):
            return str(v) if v is not None else None
        def _ids(lst):
            if not lst:
                return None
            return ",".join(str(x) for x in lst if x is not None)

        fin_ids  = torneo_resultados.get("finalistas_ids") or []
        pred_fin = [ag.get("pred_campeon_id"), ag.get("pred_finalista2_id")]
        return [
            {"item": "A",
             "resultado": _s(torneo_resultados.get("campeon_id")),
             "apuesta":   _s(ag.get("pred_campeon_id")),
             "puntaje":   score.pts_campeon},
            {"item": "B",
             "resultado": _ids(fin_ids),
             "apuesta":   _ids(pred_fin),
             "puntaje":   score.pts_finalistas},
            {"item": "C",
             "resultado": torneo_resultados.get("goleador"),
             "apuesta":   ag.get("pred_goleador"),
             "puntaje":   score.pts_goleador},
            {"item": "D",
             "resultado": _s(torneo_resultados.get("peor_equipo_id")),
             "apuesta":   _s(ag.get("pred_peor_equipo_id")),
             "puntaje":   score.pts_peor_equipo},
            {"item": "E",
             "resultado": (
                 f"{torneo_resultados['goleada_ganador']}-{torneo_resultados['goleada_perdedor']}"
                 if torneo_resultados.get("goleada_ganador") is not None else None),
             "apuesta": (
                 f"{ag['pred_goleada_ganador']}-{ag['pred_goleada_perdedor']}"
                 if ag.get("pred_goleada_ganador") is not None else None),
             "puntaje":   score.pts_mayor_goleada},
            {"item": "F",
             "resultado": torneo_resultados.get("etapa_paraguay"),
             "apuesta":   ag.get("pred_etapa_paraguay"),
             "puntaje":   score.pts_etapa_paraguay},
            {"item": "G",
             "resultado": _s(torneo_resultados.get("goles_paraguay")),
             "apuesta":   _s(ag.get("pred_goles_paraguay")),
             "puntaje":   score.pts_goles_paraguay},
        ]

    async def _persist_global_items(
        self, db, torneo_id: int, ag: dict, score, torneo_resultados: dict
    ) -> None:
        """Upsert una fila en puntaje_item por cada item global A-G."""
        items = self._build_global_items(ag, score, torneo_resultados)
        uid   = ag["apostador_id"]
        for it in items:
            await db.execute(
                text("""
                    INSERT INTO puntaje_item
                      (torneo_id, partido_id, apostador_id, categoria, item,
                       resultado, apuesta, puntaje, multiplicador, updated_at)
                    VALUES
                      (:tid, NULL, :uid, 'global', :item,
                       :resultado, :apuesta, :puntaje, 1, NOW())
                    ON CONFLICT (torneo_id, apostador_id, item)
                    WHERE partido_id IS NULL
                    DO UPDATE SET
                      resultado  = EXCLUDED.resultado,
                      apuesta    = EXCLUDED.apuesta,
                      puntaje    = EXCLUDED.puntaje,
                      updated_at = NOW()
                """),
                {"tid": torneo_id, "uid": uid, "item": it["item"],
                 "resultado": it["resultado"], "apuesta": it["apuesta"],
                 "puntaje": it["puntaje"]},
            )

    # ── Persistencia (tabla legacy puntaje_detalle) ───────────────────────────

    async def _persist_score(
        self, db, torneo_id: int, score: PartidoScore, ap: dict, p: dict
    ) -> None:
        pts_main = score.pts_resultado + score.pts_marcador

        await db.execute(
            text("UPDATE apuesta SET puntos=:pts, puntos_bonus=:bon WHERE id=:aid"),
            {"pts": pts_main, "bon": score.pts_bonus, "aid": ap["id"]},
        )

        await db.execute(
            text("""
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
                   :mult, :pl, :pv, :rl, :rv,
                   :base, :ptsm,
                   :pmin, :rmin, :gmin, :ptsmin,
                   :pamar, :ramar, :ptsamar,
                   :pvar, :rvar, :ptsvar,
                   :tmatch, :ppen, :rpen, 0,
                   :ptsbon, :ptstot,
                   :pts_resultado, :pts_rojas, :pts_pen_partido, :pts_pen_tanda, :pts_equipo)
                ON CONFLICT (torneo_id, partido_id, apostador_id) DO UPDATE SET
                   fase_id=EXCLUDED.fase_id, fase_tipo=EXCLUDED.fase_tipo,
                   fase_nombre=EXCLUDED.fase_nombre, multiplicador=EXCLUDED.multiplicador,
                   pred_local=EXCLUDED.pred_local, pred_visitante=EXCLUDED.pred_visitante,
                   real_local=EXCLUDED.real_local, real_visitante=EXCLUDED.real_visitante,
                   pts_marcador_base=EXCLUDED.pts_marcador_base, pts_marcador=EXCLUDED.pts_marcador,
                   pred_minuto=EXCLUDED.pred_minuto, real_minuto=EXCLUDED.real_minuto,
                   gano_minuto=EXCLUDED.gano_minuto, pts_minuto=EXCLUDED.pts_minuto,
                   pred_amarillas=EXCLUDED.pred_amarillas, real_amarillas=EXCLUDED.real_amarillas,
                   pts_amarillas=EXCLUDED.pts_amarillas, pred_var=EXCLUDED.pred_var,
                   real_var=EXCLUDED.real_var, pts_var=EXCLUDED.pts_var,
                   teams_match=EXCLUDED.teams_match,
                   pred_penales=EXCLUDED.pred_penales, real_penales=EXCLUDED.real_penales,
                   pts_penales=0,
                   pts_bonus=EXCLUDED.pts_bonus, pts_total=EXCLUDED.pts_total,
                   pts_resultado=EXCLUDED.pts_resultado, pts_rojas=EXCLUDED.pts_rojas,
                   pts_penales_partido=EXCLUDED.pts_penales_partido,
                   pts_penales_tanda=EXCLUDED.pts_penales_tanda, pts_equipo=EXCLUDED.pts_equipo
            """),
            {
                "tid": torneo_id, "fid": p["fase_id"],
                "ftipo": p["fase_tipo"], "fnom": p["fase_nombre"],
                "pid": score.partido_id, "uid": score.apostador_id,
                "mult": score.multiplicador,
                "pl": ap.get("pred_local"), "pv": ap.get("pred_visitante"),
                "rl": p.get("goles_local"), "rv": p.get("goles_visitante"),
                "base": score.pts_marcador_base, "ptsm": score.pts_marcador,
                "ptsr": score.pts_resultado,
                "pmin": ap.get("pred_minuto_gol"), "rmin": p.get("minuto_primer_gol"),
                "gmin": getattr(score, "gano_minuto", False),
                "ptsmin": score.pts_minuto,
                "pamar": ap.get("pred_amarillas"), "ramar": p.get("amarillas"),
                "ptsamar": score.pts_amarillas,
                "pvar": ap.get("pred_var"), "rvar": p.get("decisiones_var"),
                "ptsvar": score.pts_var,
                "tmatch": score.teams_match,
                "ppen": ap.get("pred_penales"), "rpen": p.get("penales_local") is not None,
                "ptsbon": score.pts_bonus, "ptstot": score.pts_total,
                "pts_resultado": score.pts_resultado, "pts_rojas": score.pts_rojas,
                "pts_pen_partido": score.pts_penales_partido,
                "pts_pen_tanda": score.pts_penales_tanda, "pts_equipo": score.pts_equipo,
            },
        )

    # ── _persist_items: auditoría granular H-P en puntaje_item ───────────────

    async def _persist_items(self, db, torneo_id: int, score: PartidoScore, ap: dict, p: dict):
        """Upsert de ítems H-P en puntaje_item para un partido+apostador."""
        items = self._build_partido_items(score, ap, p)
        mult = score.multiplicador
        for it in items:
            await db.execute(
                text("""
                    INSERT INTO puntaje_item
                      (torneo_id, partido_id, apostador_id, categoria, item,
                       fase_tipo, fase_nombre, fecha_partido,
                       local_nombre, visit_nombre,
                       resultado, apuesta, puntaje, multiplicador, updated_at)
                    VALUES
                      (:tid, :pid, :uid, 'partido', :item,
                       :ftipo, :fnom, :fecha,
                       :loc, :vis,
                       :res, :ap, :pts, :mult, NOW())
                    ON CONFLICT (partido_id, apostador_id, item)
                    WHERE partido_id IS NOT NULL
                    DO UPDATE SET
                       resultado=EXCLUDED.resultado, apuesta=EXCLUDED.apuesta,
                       puntaje=EXCLUDED.puntaje, multiplicador=EXCLUDED.multiplicador,
                       updated_at=NOW()
                """),
                {
                    "tid": torneo_id, "pid": p["id"], "uid": score.apostador_id,
                    "item": it["item"],
                    "ftipo": p.get("fase_tipo"), "fnom": p.get("fase_nombre"),
                    "fecha": p.get("fecha"),
                    "loc": p.get("local_nombre"), "vis": p.get("visit_nombre"),
                    "res": it["resultado"], "ap": it["apuesta"],
                    "pts": it["puntaje"], "mult": mult,
                },
            )

    def _build_partido_items(self, score: PartidoScore, ap: dict, p: dict) -> list:
        """Construye lista de {item, resultado, apuesta, puntaje} para H-P."""
        rl = p.get("goles_local")
        rv = p.get("goles_visitante")
        pl = ap.get("pred_local")
        pv = ap.get("pred_visitante")
        items = []

        # H — Resultado
        items.append({"item": "H",
                       "resultado": _wdl(rl, rv) if rl is not None and rv is not None else None,
                       "apuesta": _wdl(pl, pv) if pl is not None and pv is not None else None,
                       "puntaje": score.pts_resultado})
        # I — Marcador exacto
        items.append({"item": "I",
                       "resultado": f"{rl}-{rv}" if rl is not None else None,
                       "apuesta": f"{pl}-{pv}" if pl is not None else None,
                       "puntaje": score.pts_marcador})
        # J — Amarillas
        items.append({"item": "J",
                       "resultado": str(p.get("amarillas")) if p.get("amarillas") is not None else None,
                       "apuesta": str(ap.get("pred_amarillas")) if ap.get("pred_amarillas") is not None else None,
                       "puntaje": score.pts_amarillas})
        # K — Rojas
        items.append({"item": "K",
                       "resultado": str(p.get("rojas")) if p.get("rojas") is not None else None,
                       "apuesta": str(ap.get("pred_rojas")) if ap.get("pred_rojas") is not None else None,
                       "puntaje": score.pts_rojas})
        # L — VAR
        items.append({"item": "L",
                       "resultado": str(p.get("decisiones_var")) if p.get("decisiones_var") is not None else None,
                       "apuesta": str(ap.get("pred_var")) if ap.get("pred_var") is not None else None,
                       "puntaje": score.pts_var})
        # N — Minuto primer gol
        items.append({"item": "N",
                       "resultado": str(p.get("minuto_primer_gol")) if p.get("minuto_primer_gol") is not None else None,
                       "apuesta": str(ap.get("pred_minuto_gol")) if ap.get("pred_minuto_gol") is not None else None,
                       "puntaje": score.pts_minuto})
        # O — Penales tanda
        pen_l = p.get("penales_local")
        pen_v = p.get("penales_visitante")
        pred_pl = ap.get("pred_penales_local_tanda")
        pred_pv = ap.get("pred_penales_visitante_tanda")
        items.append({"item": "O",
                       "resultado": f"{pen_l}-{pen_v}" if pen_l is not None else None,
                       "apuesta": f"{pred_pl}-{pred_pv}" if pred_pl is not None else None,
                       "puntaje": score.pts_penales_tanda})
        # P — Equipo clasifica
        items.append({"item": "P",
                       "resultado": str(p.get("equipo_clasificado_id")) if p.get("equipo_clasificado_id") is not None else None,
                       "apuesta": str(ap.get("pred_equipo_clasifica")) if ap.get("pred_equipo_clasifica") is not None else None,
                       "puntaje": score.pts_equipo})
        return items

    # ── _persist_global_items: auditoría granular A-G en puntaje_item ─────────

    async def _persist_global_items(self, db, torneo_id: int, ag: dict, score, torneo_resultados: dict):
        """Upsert de ítems A-G en puntaje_item para un apostador."""
        from .base import GlobalScore
        items = self._build_global_items(ag, score, torneo_resultados)
        for it in items:
            await db.execute(
                text("""
                    INSERT INTO puntaje_item
                      (torneo_id, partido_id, apostador_id, categoria, item,
                       resultado, apuesta, puntaje, multiplicador, updated_at)
                    VALUES
                      (:tid, NULL, :uid, 'global', :item,
                       :res, :ap, :pts, 1, NOW())
                    ON CONFLICT (torneo_id, apostador_id, item)
                    WHERE partido_id IS NULL
                    DO UPDATE SET
                       resultado=EXCLUDED.resultado, apuesta=EXCLUDED.apuesta,
                       puntaje=EXCLUDED.puntaje, updated_at=NOW()
                """),
                {
                    "tid": torneo_id, "uid": ag["apostador_id"],
                    "item": it["item"],
                    "res": it["resultado"], "ap": it["apuesta"], "pts": it["puntaje"],
                },
            )

    def _build_global_items(self, ag: dict, score, torneo_resultados: dict) -> list:
        """Construye lista de {item, resultado, apuesta, puntaje} para A-G."""
        return [
            {"item": "A",
             "resultado": str(torneo_resultados.get("campeon_id")),
             "apuesta": str(ag.get("pred_campeon_id")),
             "puntaje": score.pts_campeon},
            {"item": "B",
             "resultado": str(sorted(torneo_resultados.get("finalistas_ids") or [])),
             "apuesta": str(sorted(filter(None, [ag.get("pred_finalista1_id"), ag.get("pred_finalista2_id")]))),
             "puntaje": score.pts_finalistas},
            {"item": "C",
             "resultado": torneo_resultados.get("goleador"),
             "apuesta": ag.get("pred_goleador"),
             "puntaje": score.pts_goleador},
            {"item": "D",
             "resultado": str(torneo_resultados.get("peor_equipo_id")),
             "apuesta": str(ag.get("pred_peor_equipo_id")),
             "puntaje": score.pts_peor_equipo},
            {"item": "E",
             "resultado": f"{torneo_resultados.get('goleada_ganador')}-{torneo_resultados.get('goleada_perdedor')}",
             "apuesta": f"{ag.get('pred_goleada_ganador')}-{ag.get('pred_goleada_perdedor')}",
             "puntaje": score.pts_mayor_goleada},
            {"item": "F",
             "resultado": torneo_resultados.get("etapa_paraguay"),
             "apuesta": ag.get("pred_etapa_paraguay"),
             "puntaje": score.pts_etapa_paraguay},
            {"item": "G",
             "resultado": str(torneo_resultados.get("goles_paraguay")),
             "apuesta": str(ag.get("pred_goles_paraguay")),
             "puntaje": score.pts_goles_paraguay},
        ]
