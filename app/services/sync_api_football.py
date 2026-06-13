"""
sync_api_football.py — Sincronización de resultados desde API-Football v3.

Flujo:
  1. GET /fixtures?league={api_league_id}&season={api_season}&status=FT-AET-PEN
     → lista de partidos finalizados (resultado básico: goles, penales, winner).
  2. Para cada partido DB con api_fixture_id sin finalizar:
     GET /fixtures?id={api_fixture_id}  (con events + statistics completos).
     Límite configurable por ejecución para respetar cuota diaria.
  3. UPDATE partido: goles, estado, penales, amarillas, rojas, var, minuto_gol,
     equipo_clasificado_id (desde teams.*.winner).

Auto-mapeo (si no hay api_fixture_id mapeados):
  - Fetch equipos y fixtures de API-Football.
  - Match equipos por nombre normalizado (sin acentos, sin puntuación).
  - Match partidos por par (home_api_id, away_api_id).
  - Guarda api_team_id en equipo y api_fixture_id en partido automáticamente.

Uso en apostador_bets.py:
    from app.services.sync_api_football import sync_torneo, auto_mapeo_torneo
    summary = await sync_torneo(db, torneo_id, force=False, max_detalle=10)
"""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from datetime import datetime, timezone
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger("sync_api_football")


async def _log(db: AsyncSession, endpoint: str, params: dict,
               resp: httpx.Response | None, t0: float,
               error: str | None = None, contexto: str | None = None) -> None:
    """
    Inserta un registro en api_sync_log. Best-effort: nunca interrumpe la transacción
    externa. No hace commit — la función llamante decide cuándo comitear.
    """
    try:
        ms = int((time.time() - t0) * 1000)
        quota = None
        if resp is not None:
            try:
                quota = int(resp.headers.get("x-ratelimit-requests-remaining", -1))
                if quota < 0:
                    quota = None
            except Exception:
                pass
        _ctx = contexto
        if not _ctx and error:
            _ctx = ("⛔ Límite cuota"
                    if ("quota" in error.lower() or "cuota" in error.lower())
                    else "❌ Error API")
        await db.execute(text("SAVEPOINT _log_sp"))
        try:
            await db.execute(
                text("""
                    INSERT INTO api_sync_log
                        (endpoint, params, status_code, response_ms, quota_remaining,
                         error_msg, payload_size, origen, contexto)
                    VALUES
                        (:ep, :params::jsonb, :sc, :ms, :quota, :err, :size, 'sync', :ctx)
                """),
                {
                    "ep":    endpoint,
                    "params": json.dumps(params),
                    "sc":    resp.status_code if resp is not None else None,
                    "ms":    ms,
                    "quota": quota,
                    "err":   error,
                    "size":  None,
                    "ctx":   _ctx,
                },
            )
            await db.execute(text("RELEASE SAVEPOINT _log_sp"))
        except Exception:
            try:
                await db.execute(text("ROLLBACK TO SAVEPOINT _log_sp"))
            except Exception:
                pass
        # Sin commit — el llamador commit cuando corresponda
    except Exception:
        pass  # Los errores de logging nunca interrumpen el sync


async def _log_warn(db: AsyncSession, contexto: str) -> None:
    """Inserta una advertencia sintética en api_sync_log (sin llamada HTTP)."""
    try:
        await db.execute(text("SAVEPOINT _logwarn_sp"))
        try:
            await db.execute(
                text("""
                    INSERT INTO api_sync_log
                        (endpoint, params, status_code, response_ms,
                         quota_remaining, error_msg, payload_size, origen, contexto)
                    VALUES ('sync', '{}', NULL, NULL, NULL, NULL, NULL, 'sync', :ctx)
                """),
                {"ctx": contexto},
            )
            await db.execute(text("RELEASE SAVEPOINT _logwarn_sp"))
        except Exception:
            try:
                await db.execute(text("ROLLBACK TO SAVEPOINT _logwarn_sp"))
            except Exception:
                pass
    except Exception:
        pass

API_BASE = "https://v3.football.api-sports.io"
STATUS_FINAL = {"FT", "AET", "PEN"}

# Cuota gratuita API-Football: 100 req/día.
# max_detalle limita cuántos partidos hacen una 2ª llamada individual (eventos+stats).
DEFAULT_MAX_DETALLE = 10

# Liga Copa Mundial FIFA en API-Football (ID oficial)
FIFA_WORLD_CUP_LEAGUE_ID = 1


def _headers() -> dict:
    return {
        "x-rapidapi-key": settings.APIFOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


# ── Utilidades de normalización de nombres ───────────────────────────────────

def _normalize(name: str) -> str:
    """Normaliza nombre de equipo: sin acentos, minúsculas, sin puntuación."""
    # Quitar acentos
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Minúsculas, quitar puntuación
    name = re.sub(r"[^\w\s]", " ", name.lower())
    # Quitar palabras irrelevantes
    for word in ("fc", "cf", "afc", "sc", "ac", "de", "del", "la", "el",
                 "los", "las", "the", "team", "national", "republic"):
        name = re.sub(rf"\b{word}\b", "", name)
    return re.sub(r"\s+", " ", name).strip()


def _match_teams(
    api_teams: list[dict],
    db_equipos: list[dict],
) -> dict[int, int]:
    """
    Retorna {db_equipo_id: api_team_id} para los equipos que matchean por nombre.
    Prioridad: exacto normalizado → substring bilateral.
    """
    api_norm: dict[str, int] = {}
    for t in api_teams:
        n = _normalize(t["name"])
        api_norm[n] = t["id"]
        # También indexar nombre corto si existe
        alt = t.get("code") or ""
        if alt:
            api_norm[alt.lower()] = t["id"]

    result: dict[int, int] = {}
    for eq in db_equipos:
        if eq.get("api_team_id"):
            result[eq["id"]] = eq["api_team_id"]
            continue
        db_n = _normalize(eq["nombre"])
        if db_n in api_norm:
            result[eq["id"]] = api_norm[db_n]
            continue
        # Substring bilateral
        for api_n, api_id in api_norm.items():
            if db_n and api_n and (db_n in api_n or api_n in db_n):
                result[eq["id"]] = api_id
                break

    return result


def _match_fixtures(
    api_fixtures: list[dict],
    db_partidos: list[dict],
    db_to_api_team: dict[int, int],
) -> dict[int, int]:
    """
    Retorna {db_partido_id: api_fixture_id}.
    Match por par (home_api_id, away_api_id).
    Si no hay match directo, intenta match inverso (swap).
    """
    # Indexar fixtures API por par de equipos
    api_by_pair: dict[tuple[int, int], int] = {}
    for fix in api_fixtures:
        key = (fix["home_id"], fix["away_id"])
        api_by_pair[key] = fix["id"]

    result: dict[int, int] = {}
    for p in db_partidos:
        if p.get("api_fixture_id"):
            result[p["id"]] = p["api_fixture_id"]
            continue
        local_api = db_to_api_team.get(p["equipo_local_id"])
        visit_api = db_to_api_team.get(p["equipo_visitante_id"])
        if not local_api or not visit_api:
            continue
        key = (local_api, visit_api)
        if key in api_by_pair:
            result[p["id"]] = api_by_pair[key]
        elif (visit_api, local_api) in api_by_pair:
            # Swap (puede pasar en fases KO donde home/away varía)
            result[p["id"]] = api_by_pair[(visit_api, local_api)]

    return result


# ── Auto-mapeo ────────────────────────────────────────────────────────────────

async def auto_mapeo_torneo(
    db: AsyncSession,
    torneo_id: int,
    client: httpx.AsyncClient,
) -> dict:
    """
    Detecta automáticamente api_league_id, api_season, api_team_id y api_fixture_id.

    1. Si api_league_id no está configurado pero la competición es Copa Mundial
       → usa FIFA_WORLD_CUP_LEAGUE_ID (1) y api_season = año actual del torneo.
    2. Fetch equipos y fixtures de API-Football.
    3. Match por nombre normalizado (equipos) y par de equipos (partidos).
    4. Guarda en BD.

    Returns: dict con resumen del auto-mapeo.
    """
    import datetime

    # ── Cargar config ──────────────────────────────────────────────────────────
    r_cfg = await db.execute(
        text("""
            SELECT t.id, t.nombre, t.api_season, c.id AS competicion_id,
                   c.nombre AS comp_nombre, c.api_league_id
            FROM torneo t
            LEFT JOIN competicion c ON c.id = t.competicion_id
            WHERE t.id = :tid
        """),
        {"tid": torneo_id},
    )
    cfg = r_cfg.mappings().first()
    if not cfg:
        raise ValueError(f"Torneo {torneo_id} no encontrado")

    api_league_id = cfg["api_league_id"]
    api_season    = cfg["api_season"]
    comp_nombre   = cfg["comp_nombre"] or ""
    competicion_id = cfg["competicion_id"]

    # Auto-detectar league_id para Copa Mundial
    if not api_league_id:
        es_mundial = any(w in comp_nombre.lower() for w in
                         ("mundial", "world cup", "copa del mundo", "fifa cup"))
        if es_mundial:
            api_league_id = FIFA_WORLD_CUP_LEAGUE_ID
            await db.execute(
                text("UPDATE competicion SET api_league_id = :lid WHERE id = :cid"),
                {"lid": api_league_id, "cid": competicion_id},
            )
        else:
            return {
                "auto_mapeo": False,
                "error": (
                    f"Competición '{comp_nombre}' no tiene api_league_id. "
                    "Configurarlo en la sección Mapeo API-Football."
                ),
            }

    # Auto-detectar season
    if not api_season:
        api_season = datetime.datetime.now().year
        await db.execute(
            text("UPDATE torneo SET api_season = :s WHERE id = :tid"),
            {"s": api_season, "tid": torneo_id},
        )

    # ── Cargar DB ──────────────────────────────────────────────────────────────
    r_eq = await db.execute(
        text("""
            SELECT id, COALESCE(nombre_es, nombre) AS nombre, api_team_id
            FROM equipo ORDER BY nombre
        """)
    )
    db_equipos = [dict(row) for row in r_eq.mappings()]

    r_p = await db.execute(
        text("""
            SELECT p.id, p.api_fixture_id, p.equipo_local_id, p.equipo_visitante_id
            FROM partido p WHERE p.torneo_id = :tid
        """),
        {"tid": torneo_id},
    )
    db_partidos = [dict(row) for row in r_p.mappings()]

    api_calls = 0

    # ── Fetch API-Football: equipos ────────────────────────────────────────────
    r1 = await client.get(
        f"{API_BASE}/teams",
        params={"league": api_league_id, "season": api_season},
        headers=_headers(),
    )
    r1.raise_for_status()
    api_calls += 1
    api_teams = [
        {
            "id":   t["team"]["id"],
            "name": t["team"]["name"],
            "code": t["team"].get("code", ""),
        }
        for t in r1.json().get("response", [])
    ]

    # ── Fetch API-Football: fixtures ───────────────────────────────────────────
    r2 = await client.get(
        f"{API_BASE}/fixtures",
        params={"league": api_league_id, "season": api_season},
        headers=_headers(),
    )
    r2.raise_for_status()
    api_calls += 1
    api_fixtures = [
        {
            "id":      fix["fixture"]["id"],
            "home_id": fix["teams"]["home"]["id"],
            "away_id": fix["teams"]["away"]["id"],
        }
        for fix in r2.json().get("response", [])
    ]

    # ── Match ─────────────────────────────────────────────────────────────────
    db_to_api_team = _match_teams(api_teams, db_equipos)
    db_to_api_fix  = _match_fixtures(api_fixtures, db_partidos, db_to_api_team)

    # ── Guardar equipos ────────────────────────────────────────────────────────
    # Construir set de api_team_ids ya en uso para evitar duplicados
    used_api_ids: set[int] = {e["api_team_id"] for e in db_equipos if e.get("api_team_id")}
    equipos_actualizados = 0
    for db_id, api_id in db_to_api_team.items():
        # Solo actualizar si no tenía valor previo Y el api_id no está ya en uso
        eq = next((e for e in db_equipos if e["id"] == db_id), None)
        if eq and not eq.get("api_team_id") and api_id not in used_api_ids:
            await db.execute(
                text("UPDATE equipo SET api_team_id = :aid WHERE id = :did"),
                {"aid": api_id, "did": db_id},
            )
            used_api_ids.add(api_id)
            equipos_actualizados += 1

    # ── Guardar partidos ───────────────────────────────────────────────────────
    partidos_actualizados = 0
    for db_id, api_id in db_to_api_fix.items():
        p = next((x for x in db_partidos if x["id"] == db_id), None)
        if p and not p.get("api_fixture_id"):
            await db.execute(
                text("UPDATE partido SET api_fixture_id = :fid WHERE id = :did"),
                {"fid": api_id, "did": db_id},
            )
            partidos_actualizados += 1

    await db.commit()

    return {
        "auto_mapeo": True,
        "api_league_id": api_league_id,
        "api_season":    api_season,
        "api_calls":     api_calls,
        "equipos_api":   len(api_teams),
        "fixtures_api":  len(api_fixtures),
        "equipos_mapeados":  len(db_to_api_team),
        "equipos_nuevos":    equipos_actualizados,
        "partidos_mapeados": len(db_to_api_fix),
        "partidos_nuevos":   partidos_actualizados,
        "equipos_sin_mapeo": len(db_equipos) - len(db_to_api_team),
        "partidos_sin_mapeo": len(db_partidos) - len(db_to_api_fix),
    }


async def sync_torneo(
    db: AsyncSession,
    torneo_id: int,
    force: bool = False,
    max_detalle: int = DEFAULT_MAX_DETALLE,
) -> dict:
    """
    Sincroniza resultados de API-Football para el torneo dado.

    Args:
        db:          sesión async de SQLAlchemy (becbuc).
        torneo_id:   ID del torneo a sincronizar.
        force:       si True, re-sincroniza aunque el partido ya esté 'finalizado'.
        max_detalle: máximo de peticiones individuales (events+stats) por run.

    Returns:
        dict con resumen {ok, actualizados, ya_finalizados, sin_match,
                          api_calls, errores, ids_actualizados, ids_errores}
    """
    if not settings.APIFOOTBALL_KEY:
        raise ValueError("APIFOOTBALL_KEY no configurado en .env")

    # ── 1. Cargar datos del torneo ───────────────────────────────────────────
    r = await db.execute(
        text("""
            SELECT t.id, t.api_season, c.api_league_id
            FROM torneo t
            LEFT JOIN competicion c ON c.id = t.competicion_id
            WHERE t.id = :tid
        """),
        {"tid": torneo_id},
    )
    torneo_row = r.mappings().first()
    if not torneo_row:
        raise ValueError(f"Torneo {torneo_id} no encontrado")

    api_season    = torneo_row["api_season"]
    api_league_id = torneo_row["api_league_id"]

    mapeo_summary: dict | None = None

    async with httpx.AsyncClient(timeout=30) as _client_check:
        # ── Auto-mapeo si faltan api_fixture_id ───────────────────────────────
        r_check = await db.execute(
            text("SELECT COUNT(*) FROM partido WHERE torneo_id = :tid AND api_fixture_id IS NOT NULL"),
            {"tid": torneo_id},
        )
        fixtures_mapeados = r_check.scalar() or 0

        if fixtures_mapeados == 0:
            # También verificar/auto-detectar api_league_id y api_season
            mapeo_summary = await auto_mapeo_torneo(db, torneo_id, _client_check)
            if not mapeo_summary.get("auto_mapeo"):
                # Falló el auto-mapeo (ej: no se pudo detectar liga)
                return {
                    "ok": False,
                    "actualizados": 0,
                    "auto_mapeo": mapeo_summary,
                    "error": mapeo_summary.get("error", "No se pudo auto-mapear"),
                }
            # Recargar api_league_id y api_season desde BD (puede haber cambiado)
            r_reload = await db.execute(
                text("""
                    SELECT t.api_season, c.api_league_id
                    FROM torneo t LEFT JOIN competicion c ON c.id = t.competicion_id
                    WHERE t.id = :tid
                """),
                {"tid": torneo_id},
            )
            row_reload = r_reload.mappings().first()
            if row_reload:
                api_season    = row_reload["api_season"]
                api_league_id = row_reload["api_league_id"]

    if not api_season or not api_league_id:
        return {
            "ok": False,
            "actualizados": 0,
            "error": (
                f"Torneo {torneo_id}: falta api_season o api_league_id. "
                "Configurar en Mapeo API-Football."
            ),
        }

    # ── 2. Cargar partidos DB con api_fixture_id ──────────────────────────────
    r2 = await db.execute(
        text("""
            SELECT p.id, p.api_fixture_id, p.estado,
                   p.equipo_local_id, p.equipo_visitante_id,
                   COALESCE(el.nombre_es, el.nombre, '?') AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre, '?') AS visit_nombre,
                   p.fecha
            FROM partido p
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = :tid AND p.api_fixture_id IS NOT NULL
        """),
        {"tid": torneo_id},
    )
    db_partidos: dict[int, dict] = {
        row["api_fixture_id"]: dict(row) for row in r2.mappings()
    }
    logger.info(f"Torneo {torneo_id}: {len(db_partidos)} partidos con api_fixture_id mapeados")

    if not db_partidos:
        return {
            "ok": False,
            "actualizados": 0,
            "auto_mapeo": mapeo_summary,
            "error": (
                "Auto-mapeo completado pero no se encontraron partidos coincidentes. "
                "Verificar que los equipos DB coincidan con los de API-Football."
            ),
        }

    # ── 3. Cargar mapa equipo.api_team_id → equipo.id ────────────────────────
    r3 = await db.execute(
        text("SELECT id, api_team_id FROM equipo WHERE api_team_id IS NOT NULL")
    )
    team_id_map: dict[int, int] = {
        row["api_team_id"]: row["id"] for row in r3.mappings()
    }

    # ── 4. Partidos finalizados + en vivo ─────────────────────────────────────
    api_calls = 0
    actualizados: list[int] = []
    ya_finalizados: list[int] = []
    sin_match: list[int] = []
    errores: list[dict] = []

    LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}

    async with httpx.AsyncClient(timeout=30) as client:
        # ── 4a. Finalizados ──────────────────────────────────────────────────
        _t0 = time.time()
        _p_ft = {"league": api_league_id, "season": api_season, "status": "FT-AET-PEN"}
        try:
            resp = await client.get(f"{API_BASE}/fixtures", params=_p_ft, headers=_headers())
            resp.raise_for_status()
            api_calls += 1
            await _log(db, "/fixtures", _p_ft, resp, _t0, contexto="📋 Bulk finalizados")
        except httpx.HTTPStatusError as e:
            await _log(db, "/fixtures", _p_ft, e.response, _t0,
                       error=f"HTTP {e.response.status_code}", contexto="📋 Bulk finalizados")
            raise ValueError(f"API-Football error {e.response.status_code}: {e.response.text[:300]}")
        except httpx.RequestError as e:
            await _log(db, "/fixtures", _p_ft, None, _t0,
                       error=str(e), contexto="📋 Bulk finalizados")
            raise ValueError(f"Error de conexión a API-Football: {e}")

        # Capturar cuota restante para advertencias post-sync
        _quota_remaining: int | None = None
        try:
            _q = int(resp.headers.get("x-ratelimit-requests-remaining", -1))
            if _q >= 0:
                _quota_remaining = _q
        except Exception:
            pass

        data = resp.json()
        if data.get("errors"):
            raise ValueError(f"API-Football devolvió errores: {data['errors']}")

        finished_fixtures: list[dict] = data.get("response", [])
        finished_ids: set[int] = {f["fixture"]["id"] for f in finished_fixtures}

        # ── 4b. En vivo ──────────────────────────────────────────────────────
        live_fixtures: list[dict] = []
        _t0_live = time.time()
        _p_live = {"live": "all", "league": api_league_id, "season": api_season}
        try:
            resp_live = await client.get(f"{API_BASE}/fixtures", params=_p_live, headers=_headers())
            resp_live.raise_for_status()
            api_calls += 1
            live_fixtures = [
                f for f in resp_live.json().get("response", [])
                if f["fixture"]["id"] not in finished_ids
            ]
            await _log(db, "/fixtures", _p_live, resp_live, _t0_live,
                       contexto=f"🔴 En vivo ({len(live_fixtures)} partidos)")
            logger.info(f"Partidos en vivo encontrados: {len(live_fixtures)}")
        except Exception as e:
            await _log(db, "/fixtures", _p_live, None, _t0_live,
                       error=str(e), contexto="🔴 En vivo")
            logger.warning(f"Error al fetch live fixtures: {e}")

        # Partidos que hay que actualizar: finalizados + en vivo
        to_detail: list[tuple[int, dict, bool]] = []  # (api_fixture_id, db_partido, is_live)

        for fix in finished_fixtures:
            fix_id = fix["fixture"]["id"]
            if fix_id not in db_partidos:
                sin_match.append(fix_id)
                continue
            db_p = db_partidos[fix_id]
            if not force and db_p["estado"] == "finalizado":
                ya_finalizados.append(db_p["id"])
                continue
            to_detail.append((fix_id, db_p, False))

        live_fixture_ids: set[int] = set()
        for fix in live_fixtures:
            fix_id = fix["fixture"]["id"]
            live_fixture_ids.add(fix_id)
            if fix_id not in db_partidos:
                sin_match.append(fix_id)
                continue
            db_p = db_partidos[fix_id]
            to_detail.append((fix_id, db_p, True))  # always update live

        # ── Fallback: partidos en ventana activa ausentes de live/FT ─────────────────
        # Cubre dos casos:
        #   1. en_juego en BD pero ausente de live=all (HT, ET o lag de API)
        #   2. dentro de ventana temporal 0-150 min desde inicio, sin importar estado BD
        #      → garantiza que el 2do tiempo siempre se actualice aunque el 1er sync no corrió
        now_utc = datetime.now(timezone.utc)
        already_queued = {fix_id for fix_id, _, _ in to_detail}
        for fix_id, db_p in db_partidos.items():
            if fix_id in already_queued:
                continue
            if fix_id in finished_ids:
                continue
            if db_p.get("estado") == "finalizado":
                continue

            # Caso 1: en_juego en BD pero no llegó por el endpoint live
            in_juego = (db_p.get("estado") == "en_juego"
                        and fix_id not in live_fixture_ids)

            # Caso 2: dentro de ventana activa (0-150 min desde fecha inicio)
            in_window = False
            elapsed_min = -1.0
            fecha = db_p.get("fecha")
            if fecha:
                try:
                    if hasattr(fecha, "tzinfo") and fecha.tzinfo:
                        elapsed_min = (now_utc - fecha).total_seconds() / 60
                    else:
                        elapsed_min = (datetime.utcnow() - fecha).total_seconds() / 60
                    in_window = 0.0 <= elapsed_min <= 150.0
                except Exception:
                    pass

            if in_juego or in_window:
                reason = "en_juego" if in_juego else f"+{elapsed_min:.0f}min"
                logger.info(
                    f"  [FALLBACK {reason}] fixture={fix_id} partido_id={db_p['id']} "
                    f"— {db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"
                )
                already_queued.add(fix_id)
                to_detail.append((fix_id, db_p, True))

        logger.info(
            f"Partidos a actualizar: {len(to_detail)} | "
            f"Ya finalizados: {len(ya_finalizados)} | Sin match: {len(sin_match)}"
        )
        for fix_id, db_p, is_live in to_detail:
            _nm = f"{db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"
            tag = "🔴 LIVE" if is_live else "✓ FT"
            logger.info(f"  [{tag}] Monitoreando: fixture={fix_id} partido_id={db_p['id']} — {_nm}")

        # ── 5. Llamadas individuales (events + statistics) ───────────────────
        # Los partidos en vivo siempre se procesan con detalle individual
        # (ignorando max_detalle) para obtener score en tiempo real.
        all_finished = finished_fixtures  # para fallback básico
        detalle_count = 0
        for fix_id, db_p, is_live in to_detail:
            partido_id = db_p["id"]
            match_name = f"{db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"

            if not is_live and detalle_count >= max_detalle:
                # Límite alcanzado: actualizar solo con dato básico del listado
                logger.info(f"  Límite max_detalle={max_detalle} alcanzado; básico para {match_name}")
                fix_basic = next(
                    (f for f in all_finished if f["fixture"]["id"] == fix_id), None
                )
                if fix_basic:
                    try:
                        await _update_partido_basic(db, partido_id, fix_basic, team_id_map)
                        actualizados.append(partido_id)
                    except Exception as e:
                        errores.append({"partido_id": partido_id, "error": str(e)})
                continue

            # Fetch individual con eventos y estadísticas
            t0 = time.time()
            tag = "🔴 LIVE" if is_live else "FT"
            _p_det = {"id": fix_id}
            logger.info(f"  Fetch detalle API [{tag}]: fixture={fix_id} — {match_name}")
            try:
                resp2 = await client.get(f"{API_BASE}/fixtures", params=_p_det, headers=_headers())
                resp2.raise_for_status()
                api_calls += 1
                detalle_count += 1
                await _log(db, "/fixtures", _p_det, resp2, t0,
                           contexto=f"{tag} {match_name}")
            except Exception as e:
                elapsed = time.time() - t0
                mm, ss = divmod(elapsed, 60)
                await _log(db, "/fixtures", _p_det, None, t0,
                           error=str(e), contexto=f"{tag} {match_name}")
                errores.append({"partido_id": partido_id, "error": f"fetch individual: {e}"})
                logger.warning(f"  Error fetch {match_name} ({int(mm):02d}:{ss:05.2f}): {e}")
                continue

            fixtures_resp = resp2.json().get("response", [])
            if not fixtures_resp:
                errores.append({"partido_id": partido_id, "error": "respuesta vacía en fetch individual"})
                continue

            fix_full = fixtures_resp[0]
            try:
                await _update_partido_full(db, partido_id, fix_full, team_id_map)
                await db.commit()
                actualizados.append(partido_id)
                elapsed = time.time() - t0
                mm, ss = divmod(elapsed, 60)
                logger.info(f"  ✓ Actualizado: {match_name} (partido_id={partido_id}) [{int(mm):02d}:{ss:05.2f}]")
            except Exception as e:
                await db.rollback()
                elapsed = time.time() - t0
                mm, ss = divmod(elapsed, 60)
                errores.append({"partido_id": partido_id, "error": str(e)})
                logger.warning(f"  ✗ Error actualizando {match_name} [{int(mm):02d}:{ss:05.2f}]: {e}")

    # ── Advertencias post-sync en el log ─────────────────────────────────────
    if _quota_remaining is not None and _quota_remaining < 20:
        await _log_warn(db, f"⚠ Cuota baja: {_quota_remaining} llamadas restantes hoy")
    if errores:
        first_err = errores[0]["error"][:60]
        await _log_warn(db, f"⚠ {len(errores)} partido(s) con error: {first_err}")
    if len(actualizados) == 0 and len(to_detail) > 0:
        await _log_warn(db, f"⚠ 0 actualizados de {len(to_detail)} candidatos — revisar API")
    if mapeo_summary and mapeo_summary.get("partidos_mapeados", 0) > 0:
        n = mapeo_summary["partidos_mapeados"]
        await _log_warn(db, f"ℹ Auto-mapeo: {n} partido(s) mapeados automáticamente")

    return {
        "ok": True,
        "actualizados": len(actualizados),
        "ya_finalizados": len(ya_finalizados),
        "sin_match_api": len(sin_match),
        "api_calls": api_calls,
        "errores": len(errores),
        "ids_actualizados": actualizados,
        "ids_errores": errores,
        "limite_detalle": max_detalle,
        "detalle_usados": min(len(actualizados), max_detalle),
        **({"auto_mapeo": mapeo_summary} if mapeo_summary else {}),
    }


# ── Helpers de actualización ─────────────────────────────────────────────────

def _get_winner_id(fix: dict, team_id_map: dict[int, int]) -> int | None:
    """Retorna el equipo_id del ganador según teams.*.winner, o None si hay empate/sin dato."""
    teams = fix.get("teams", {})
    home_winner = teams.get("home", {}).get("winner")
    away_winner = teams.get("away", {}).get("winner")
    if home_winner is True:
        api_id = teams["home"]["id"]
        return team_id_map.get(api_id)
    if away_winner is True:
        api_id = teams["away"]["id"]
        return team_id_map.get(api_id)
    return None


async def _update_partido_basic(
    db: AsyncSession,
    partido_id: int,
    fix: dict,
    team_id_map: dict[int, int],
) -> None:
    """Actualiza un partido con datos básicos del listado (sin events/stats)."""
    status_short = fix["fixture"]["status"]["short"]
    goals_home   = fix["goals"]["home"]
    goals_away   = fix["goals"]["away"]

    pen_home = fix["score"]["penalty"]["home"] if status_short == "PEN" else None
    pen_away = fix["score"]["penalty"]["away"] if status_short == "PEN" else None

    equipo_clasif_id = _get_winner_id(fix, team_id_map)

    await db.execute(
        text("""
            UPDATE partido SET
                goles_local         = :gl,
                goles_visitante     = :gv,
                penales_local       = :pl,
                penales_visitante   = :pv,
                estado              = 'finalizado',
                minuto_actual       = NULL,
                equipo_clasificado_id = COALESCE(:ecid, equipo_clasificado_id)
            WHERE id = :pid
        """),
        {
            "gl": goals_home, "gv": goals_away,
            "pl": pen_home,   "pv": pen_away,
            "ecid": equipo_clasif_id,
            "pid": partido_id,
        },
    )


async def _update_partido_full(
    db: AsyncSession,
    partido_id: int,
    fix: dict,
    team_id_map: dict[int, int],
) -> None:
    """Actualiza un partido con datos completos (goals + events + statistics)."""
    status_short = fix["fixture"]["status"]["short"]
    goals_home   = fix["goals"]["home"]
    goals_away   = fix["goals"]["away"]

    pen_home = fix["score"]["penalty"]["home"] if status_short == "PEN" else None
    pen_away = fix["score"]["penalty"]["away"] if status_short == "PEN" else None

    equipo_clasif_id = _get_winner_id(fix, team_id_map)

    # Estadísticas (amarillas, rojas)
    amarillas_total: int | None = None
    rojas_total:     int | None = None
    for stat_team in fix.get("statistics", []):
        for stat in stat_team.get("statistics", []):
            raw_val = stat.get("value") or 0
            try:
                val = int(raw_val)
            except (TypeError, ValueError):
                val = 0
            t = stat.get("type", "")
            if t == "Yellow Cards":
                amarillas_total = (amarillas_total or 0) + val
            elif t == "Red Cards":
                rojas_total = (rojas_total or 0) + val

    # Eventos: minuto primer gol + decisiones VAR
    minuto_primer_gol: int | None = None
    decisiones_var:    int | None = None

    events: list[dict] = fix.get("events", [])
    var_count = 0

    # Ordenar eventos por minuto
    events_sorted = sorted(events, key=lambda e: e.get("time", {}).get("elapsed") or 999)

    rojas_events = 0  # fallback si statistics llegan tarde (partidos en vivo)

    # Penales cobrados durante el partido (ítem M): convertidos + fallados.
    # NO incluye la tanda de penales (ítem O), que se cuenta aparte por score.penalty.
    penales_partido_total = 0

    # Rastrear goles anulados por VAR para no usarlos como minuto_primer_gol
    goles_anulados_minutos: set[int] = set()
    for ev in events_sorted:
        ev_type   = ev.get("type", "")
        ev_detail = ev.get("detail", "")
        elapsed   = ev.get("time", {}).get("elapsed")

        if ev_type == "Var":
            var_count += 1
            # Si el VAR anula un gol, registrar el minuto para excluirlo
            if ev_detail in ("Goal Disallowed", "Goal Cancelled", "Offside Goal"):
                if elapsed is not None:
                    goles_anulados_minutos.add(elapsed)

        if ev_type == "Card" and ev_detail in ("Red Card", "Second Yellow card"):
            rojas_events += 1

        # Penal cobrado durante el juego (convertido o fallado)
        if ev_type == "Goal" and ev_detail == "Penalty":
            penales_partido_total += 1
        elif ev_type == "Miss" and ev_detail in ("Missed Penalty", "Penalty Missed"):
            penales_partido_total += 1
        elif ev_type == "Goal" and ev_detail in ("Missed Penalty", "Penalty Missed"):
            # Algunos payloads de API-Football reportan penal fallado como type "Goal"
            penales_partido_total += 1

    for ev in events_sorted:
        ev_type   = ev.get("type", "")
        ev_detail = ev.get("detail", "")
        elapsed   = ev.get("time", {}).get("elapsed")

        if ev_type == "Goal" and ev_detail not in ("Penalty Missed", "Missed Penalty"):
            if elapsed is not None and elapsed in goles_anulados_minutos:
                continue  # gol anulado por VAR — no contar
            if minuto_primer_gol is None and elapsed is not None:
                minuto_primer_gol = elapsed

    decisiones_var = var_count  # siempre 0+ — null impide comparar con pronóstico

    # Si las statistics aún no reflejan las rojas (partido en vivo), usar conteo de eventos
    if rojas_events > 0 and (rojas_total is None or rojas_total < rojas_events):
        rojas_total = rojas_events
    elapsed_now = fix["fixture"]["status"].get("elapsed")

    # Para partidos finalizados con eventos procesados: los nulos pasan a 0
    # (null en BD impide comparar correctamente con pronósticos)
    STATUS_MAP_CHECK = {"FT", "AET", "PEN"}
    if status_short in STATUS_MAP_CHECK:
        if amarillas_total is None:
            amarillas_total = 0
        if rojas_total is None:
            rojas_total = 0

    STATUS_MAP = {
        "FT": "finalizado", "AET": "finalizado", "PEN": "finalizado",
        "1H": "en_juego",   "HT": "en_juego",    "2H": "en_juego",
        "ET": "en_juego",   "BT": "en_juego",    "P":  "en_juego",
        "LIVE": "en_juego",
        "SUSP": "aplazado", "INT": "aplazado",   "PST": "aplazado",
        "CANC": "cancelado","ABD": "cancelado",  "AWD": "cancelado", "WO": "cancelado",
        "NS":   "programado","TBD": "programado",
    }
    estado = STATUS_MAP.get(status_short, "en_juego")

    await db.execute(
        text("""
            UPDATE partido SET
                goles_local           = :gl,
                goles_visitante       = :gv,
                penales_local         = :pl,
                penales_visitante     = :pv,
                estado                = :est,
                minuto_actual         = :min_act,
                amarillas             = COALESCE(:am, amarillas),
                rojas                 = COALESCE(:ro, rojas),
                decisiones_var        = :dv,
                minuto_primer_gol     = COALESCE(:mpg, minuto_primer_gol),
                equipo_clasificado_id = COALESCE(:ecid, equipo_clasificado_id),
                penales_partido       = :pp
            WHERE id = :pid
        """),
        {
            "gl":      goals_home,
            "gv":      goals_away,
            "pl":      pen_home,
            "pv":      pen_away,
            "est":     estado,
            "min_act": elapsed_now,
            "am":      amarillas_total,
            "ro":      rojas_total,
            "dv":      decisiones_var,
            "mpg":     minuto_primer_gol,
            "ecid":    equipo_clasif_id,
            "pp":      penales_partido_total,  # siempre 0+ si hay eventos procesados
            "pid":     partido_id,
        },
    )
    await db.commit()
