"""
calculator.py — Orquestador ScoringCalculator.
Encapsula: cargar datos, puntuar via engine, persistir en BD.
El endpoint calcular_puntajes llama:
    result = await ScoringCalculator(db).calculate(torneo_id, engine)
"""
from __future__ import annotations
from collections import defaultdict
from sqlalchemy import text
from .base import ScoringEngine, PartidoScore


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

            # Persistir
            await self._persist_score(db, torneo_id, score, ap, p)

        return {"plenos": plenos, "aciertos": aciertos, "fallos": fallos, "por_fase": por_fase}

    # ── Pronósticos globales A-G ─────────────────────────────────────────────

    async def calculate_global(self, torneo_id: int, engine) -> dict:
        """
        Calcula y persiste puntajes globales A-G.
        Devuelve dict {procesadas, torneo_resultados}.
        """
        db = self.db

        torneo_resultados = await self._load_torneo_resultados(db, torneo_id)

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

        for ag in apuestas_globales:
            score = engine.score_global(ag, torneo_resultados)
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
                       p.rojas, p.penales_partido, p.equipo_clasificado_id
                FROM partido p
                JOIN fase f ON f.id = p.fase_id
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

    # ── Persistencia ──────────────────────────────────────────────────────────

    async def _persist_score(
        self, db, torneo_id: int, score: PartidoScore, ap: dict, p: dict
    ) -> None:
        pts_main = score.pts_resultado + score.pts_marcador  # H+I → apuesta.puntos

        # Actualizar apuesta
        await db.execute(
            text("UPDATE apuesta SET puntos=:pts, puntos_bonus=:bon WHERE id=:aid"),
            {"pts": pts_main, "bon": score.pts_bonus, "aid": ap["id"]},
        )

        # Upsert puntaje_detalle
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
                "tid": torneo_id,
                "fid": p["fase_id"],
                "ftipo": p["fase_tipo"],
                "fnom": p["fase_nombre"],
                "pid": score.partido_id,
                "uid": score.apostador_id,
                "mult": score.multiplicador,
                "pl": ap.get("pred_local"),
                "pv": ap.get("pred_visitante"),
                "rl": p.get("goles_local"),
                "rv": p.get("goles_visitante"),
                "base": score.pts_marcador_base,
                "ptsm": score.pts_marcador,
                "pmin": ap.get("pred_minuto_gol"),
                "rmin": p.get("minuto_primer_gol"),
                "gmin": score.gano_minuto,
                "ptsmin": score.pts_minuto,
                "pamar": ap.get("pred_amarillas"),
                "ramar": p.get("amarillas"),
                "ptsamar": score.pts_amarillas,
                "pvar": ap.get("pred_var"),
                "rvar": p.get("decisiones_var"),
                "ptsvar": score.pts_var,
                "tmatch": score.teams_match,
                "ppen": ap.get("pred_penales"),
                "rpen": p.get("penales_local") is not None,
                "ptsbon": score.pts_bonus,
                "ptstot": score.pts_total,
                "pts_resultado": score.pts_resultado,
                "pts_rojas": score.pts_rojas,
                "pts_pen_partido": score.pts_penales_partido,
                "pts_pen_tanda": score.pts_penales_tanda,
                "pts_equipo": score.pts_equipo,
            },
        )
