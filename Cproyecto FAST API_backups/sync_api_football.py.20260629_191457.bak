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

# Plan Pro API-Football: sin límite de cuota diaria.
# max_detalle limita cuántos partidos hacen una 2ª llamada individual (eventos+stats).
# Con plan Pro se puede subir a 50 o más sin riesgo de cuota.
DEFAULT_MAX_DETALLE = 50

# Liga Copa Mundial FIFA en API-Football (ID oficial)
FIFA_WORLD_CUP_LEAGUE_ID = 1

# ── ESPN (fuente verificadora) ────────────────────────────────────────────────
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
ESPN_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
_VAR_RE = re.compile(
    # Frases explícitas de VAR (ESPN commentary en inglés)
    r"VAR\s+Decision|VAR\s+Check|VAR\s+Review|VAR\s+call|"
    r"goes\s+to\s+monitor|after\s+VAR|Video\s+Review|"
    r"Video\s+Assistant|consult(?:s|ing)\s+VAR|"
    # ESPN a veces usa solo "VAR:" al inicio de la descripción
    r"VAR:|VAR\s+overrule|VAR\s+uphold|referee\s+review",
    re.IGNORECASE,
)

# ── SofaScore (fuente autoritativa para tarjetas y VAR) ───────────────────────
# SofaScore distingue correctamente "yellow" (1ª) de "yellowRed" (2ª amarilla=expulsión)
# y reporta VAR como eventos discretos (1 evento = 1 decisión real).
SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
SOFASCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}
# SofaScore devuelve 403 Forbidden desde IP de servidor — deshabilitado.
# Cambiar a True si se resuelve el acceso (proxy, Playwright, etc.)
SOFASCORE_ENABLED = False


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


# ── ESPN helpers ──────────────────────────────────────────────────────────────

# Mapa de traducción Español → Inglés para nombres de equipos nacionales.
# ESPN usa nombres en inglés; la BD tiene nombres en español.
# Mapa con claves SIN normalizar (legible). Se construye versión normalizada abajo.
_TEAM_ES_EN_RAW: dict[str, list[str]] = {
    # América
    "estados unidos":       ["united states", "usa", "us"],
    "estados unidos de america": ["united states", "usa"],
    "usa":                  ["united states", "usa"],
    "trinidad y tobago":    ["trinidad and tobago", "trinidad & tobago"],
    "republica dominicana": ["dominican republic"],
    "costa rica":           ["costa rica"],
    "el salvador":          ["el salvador"],
    "haiti":                ["haiti"],
    "curacao":              ["curacao", "curaçao"],
    # Europa
    "paises bajos":         ["netherlands", "holland"],
    "holanda":              ["netherlands", "holland"],
    "republica checa":      ["czech republic", "czechia"],
    "chequia":              ["czech republic", "czechia"],
    "bosnia y herzegovina": ["bosnia and herzegovina", "bosnia & herzegovina", "bosnia-herzegovina"],
    "escocia":              ["scotland"],
    "gales":                ["wales"],
    "irlanda del norte":    ["northern ireland"],
    "irlanda":              ["ireland", "republic of ireland"],
    "inglaterra":           ["england"],
    "alemania":             ["germany"],
    "espana":               ["spain"],
    "francia":              ["france"],
    "belgica":              ["belgium"],
    "suiza":                ["switzerland"],
    "austria":              ["austria"],
    "suecia":               ["sweden"],
    "noruega":              ["norway"],
    "dinamarca":            ["denmark"],
    "finlandia":            ["finland"],
    "polonia":              ["poland"],
    "hungria":              ["hungary"],
    "rumania":              ["romania"],
    "turquia":              ["turkey", "turkiye"],
    "turkiye":              ["turkey", "turkiye"],   # BD puede tener con acento
    "grecia":               ["greece"],
    "ucrania":              ["ukraine"],
    "rusia":                ["russia"],
    "eslovaquia":           ["slovakia"],
    "eslovenia":            ["slovenia"],
    "croacia":              ["croatia"],
    "serbia":               ["serbia"],
    "albania":              ["albania"],
    "georgia":              ["georgia"],
    "macedonia del norte":  ["north macedonia"],
    "islandia":             ["iceland"],
    "azerbaiyan":           ["azerbaijan"],
    "bielorusia":           ["belarus"],
    "kazakhstan":           ["kazakhstan"],
    "moldova":              ["moldova"],
    "kosovo":               ["kosovo"],
    "luxemburgo":           ["luxembourg"],
    "chipre":               ["cyprus"],
    "portugal":             ["portugal"],
    "italia":               ["italy"],
    "letonia":              ["latvia"],
    "lituania":             ["lithuania"],
    "estonia":              ["estonia"],
    # África
    "costa de marfil":      ["ivory coast", "cote d ivoire", "cote divoire"],
    "republica democratica del congo": ["dr congo", "congo dr", "democratic republic of congo"],
    "congo dr":             ["dr congo", "congo", "congo dr"],
    "africa del sur":       ["south africa"],
    "marruecos":            ["morocco"],
    "camerun":              ["cameroon"],
    "egipto":               ["egypt"],
    "tunez":                ["tunisia"],
    "argelia":              ["algeria"],
    "etiopia":              ["ethiopia"],
    "cabo verde":           ["cape verde"],
    # Asia / Oceanía
    "corea del sur":        ["south korea", "korea republic", "korea"],
    "corea del norte":      ["north korea", "korea dpr"],
    "arabia saudita":       ["saudi arabia"],
    "emiratos arabes":      ["united arab emirates", "uae"],
    "emiratos arabes unidos": ["united arab emirates", "uae"],
    "iran":                 ["iran", "ir iran"],
    "irak":                 ["iraq"],
    "uzbekistan":           ["uzbekistan", "uzbek"],
    "tayikistan":           ["tajikistan"],
    "nueva zelanda":        ["new zealand"],
    "filipinas":            ["philippines"],
    "tailandia":            ["thailand"],
    "china":                ["china pr", "china"],
    "japon":                ["japan"],
    "jordania":             ["jordan"],
}

# Versión con claves NORMALIZADAS (para lookup en _espn_translate)
_TEAM_ES_EN: dict[str, list[str]] = {
    _normalize(k): [_normalize(v) for v in vs]
    for k, vs in _TEAM_ES_EN_RAW.items()
}

# Inverso: inglés normalizado → español normalizado
_TEAM_EN_ES: dict[str, str] = {}
for _es_n, _en_list in _TEAM_ES_EN.items():
    for _en_n in _en_list:
        _TEAM_EN_ES[_en_n] = _es_n

async def _espn_scoreboard(client: httpx.AsyncClient, fecha) -> list[dict]:
    """
    Devuelve eventos ESPN para la fecha del partido.
    Incluye fallback al día anterior: partidos nocturnos en USA/México
    tienen fecha UTC diferente a la fecha local del partido.
    """
    from datetime import timedelta as _td, date as _date_t
    if hasattr(fecha, "strftime"):
        d = fecha.date() if hasattr(fecha, "date") and callable(fecha.date) else fecha
    else:
        from datetime import date as _date_t2
        try:
            d = _date_t2.fromisoformat(str(fecha)[:10])
        except Exception:
            d = None

    events: list[dict] = []
    dates_to_try = []
    if d:
        dates_to_try = [d, d - _td(days=1)]  # hoy + día anterior (fallback timezone)
    else:
        date_str = str(fecha)[:10].replace("-", "")
        dates_to_try_raw = [date_str]

    for dt in dates_to_try:
        date_str = dt.strftime("%Y%m%d")
        try:
            r = await client.get(
                f"{ESPN_BASE}/scoreboard",
                params={"dates": date_str},
                headers=ESPN_HEADERS,
                timeout=15,
            )
            events += r.json().get("events", [])
        except Exception as e:
            logger.warning(f"ESPN scoreboard error ({date_str}): {e}")

    # Deduplicar por event id
    seen: set = set()
    unique: list[dict] = []
    for ev in events:
        eid = ev.get("id")
        if eid not in seen:
            seen.add(eid)
            unique.append(ev)
    return unique


def _espn_translate(name_n: str) -> list[str]:
    """
    Dado un nombre normalizado (puede ser ES o EN), devuelve lista de
    variantes normalizadas a intentar en el matching: el original +
    traducciones ES→EN o EN→ES.
    """
    variants = [name_n]
    # ES → EN
    if name_n in _TEAM_ES_EN:
        variants += [_normalize(e) for e in _TEAM_ES_EN[name_n]]
    # EN → ES (inverso)
    if name_n in _TEAM_EN_ES:
        variants.append(_TEAM_EN_ES[name_n])
    return list(dict.fromkeys(variants))  # dedup preservando orden


def _espn_find_game_id(events: list[dict], local: str, visitante: str) -> str | None:
    """
    Busca el ESPN game_id por nombres de equipos normalizados.
    Aplica traducción ES↔EN para mejorar cobertura con equipos en español.
    """
    loc_n  = _normalize(local)
    vis_n  = _normalize(visitante)
    loc_vs = _espn_translate(loc_n)
    vis_vs = _espn_translate(vis_n)

    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        team_names = [
            _normalize(c.get("team", {}).get("displayName", ""))
            for c in comp.get("competitors", [])
        ]
        team_names += [
            _normalize(c.get("team", {}).get("shortDisplayName", ""))
            for c in comp.get("competitors", [])
        ]
        team_names += [
            _normalize(c.get("team", {}).get("abbreviation", ""))
            for c in comp.get("competitors", [])
        ]
        team_names = [t for t in team_names if t]

        def _team_match(variants: list[str]) -> bool:
            for v in variants:
                if any(v in t or t in v for t in team_names):
                    return True
            return False

        if _team_match(loc_vs) and _team_match(vis_vs):
            return ev.get("id")
    return None


async def _espn_get_summary(client: httpx.AsyncClient, game_id: str) -> dict:
    """Descarga el summary ESPN (stats + plays)."""
    try:
        r = await client.get(
            f"{ESPN_BASE}/summary",
            params={"event": game_id},
            headers=ESPN_HEADERS,
            timeout=15,
        )
        return r.json()
    except Exception as e:
        logger.warning(f"ESPN summary error (game_id={game_id}): {e}")
        return {}


def _espn_extract_stats(summary: dict) -> dict:
    """
    Extrae stats comparables del ESPN summary.
    Retorna: {decisiones_var, amarillas, rojas, minuto_primer_gol?,
              penales_partido?, penales_local_tanda?, penales_visitante_tanda?}
    """
    result: dict = {}

    # Amarillas + rojas desde boxscore statistics (suma ambos equipos)
    amarillas = 0
    rojas = 0
    for team_data in summary.get("boxscore", {}).get("teams", []):
        for stat in team_data.get("statistics", []):
            try:
                val = int(stat.get("value") or 0)
            except (ValueError, TypeError):
                val = 0
            name = stat.get("name", "")
            if name == "yellowCards":
                amarillas += val
            elif name == "redCards":
                rojas += val
    result["amarillas"] = amarillas
    result["rojas"] = rojas

    # VAR + minuto primer gol + penales partido desde plays/commentary
    plays = summary.get("plays") or summary.get("commentary") or []
    var_count = 0
    first_goal_min: int | None = None
    penales_partido = 0

    _PEN_RE = re.compile(r"\bpenalt", re.I)
    _SHOOTOUT_PERIOD_IDS = {5, 6, "5", "6"}  # ESPN period 5/6 = tanda de penales

    for play in plays:
        text_val = (
            play.get("text") or
            play.get("commentary") or
            play.get("description") or ""
        )
        if _VAR_RE.search(text_val):
            var_count += 1

        # Detectar tipo de jugada para minuto gol
        t_obj = play.get("type")
        ptype = t_obj.get("text", "") if isinstance(t_obj, dict) else str(t_obj or "")
        ptype_lower = ptype.lower()

        # Periodo: ESPN usa period.number (1/2=normal, 3/4=extra time, 5+=shootout)
        period_obj = play.get("period")
        period_num = None
        if isinstance(period_obj, dict):
            period_num = period_obj.get("number") or period_obj.get("type")

        is_shootout = period_num in _SHOOTOUT_PERIOD_IDS

        if "goal" in ptype_lower and first_goal_min is None and not is_shootout:
            clock = play.get("clock")
            min_str = clock.get("displayValue", "") if isinstance(clock, dict) else str(clock or "")
            try:
                first_goal_min = int(min_str.split(":")[0]) if ":" in min_str else int(min_str)
            except (ValueError, AttributeError):
                pass

        # Penales durante el partido (item M): solo tiempo normal/extra, no tanda
        if not is_shootout and _PEN_RE.search(text_val):
            if "goal" in ptype_lower or "miss" in ptype_lower:
                penales_partido += 1

    result["decisiones_var"] = var_count
    if first_goal_min is not None:
        result["minuto_primer_gol"] = first_goal_min
    if penales_partido > 0:
        result["penales_partido"] = penales_partido

    # Tanda de penales: ESPN lo reporta en header.competitions[0].competitors
    # como shootoutScore (int) ordenado home=0 / away=1
    competitions = summary.get("header", {}).get("competitions", [])
    if competitions:
        comp = competitions[0]
        competitors = comp.get("competitors", [])
        # ESPN: homeTeam == competitors[0], awayTeam == competitors[1] normalmente
        # pero el orden puede variar; usamos el campo "homeAway"
        home_score = away_score = None
        for c in competitors:
            ss = c.get("shootoutScore")
            if ss is not None:
                try:
                    score_int = int(ss)
                except (ValueError, TypeError):
                    score_int = None
                if c.get("homeAway") == "home":
                    home_score = score_int
                elif c.get("homeAway") == "away":
                    away_score = score_int
        if home_score is not None and away_score is not None:
            result["penales_local_tanda"]    = home_score
            result["penales_visitante_tanda"] = away_score

    return result


async def _espn_verify_and_patch(
    db: AsyncSession,
    client: httpx.AsyncClient,
    db_p: dict,
    partido_id: int,
    espn_cache: dict,
    out_raw: dict | None = None,
) -> dict:
    """
    Verifica stats de un partido finalizado contra ESPN y aplica correcciones.
    Reglas (J / K / L):
      - Si la API devolvió 0 para amarillas/rojas/decisiones_var Y ESPN devuelve > 0,
        se adopta el valor de ESPN como valor final.
      - Si la API ya devolvió un valor > 0, NO se pisa con ESPN (API tiene prioridad).
      - minuto_primer_gol: ESPN como fallback si API-Football devolvió NULL.

    out_raw: si se provee, se rellena con los valores crudos detectados por ESPN
             (J/K/L/M), independientemente de si se aplicaron o no.

    Retorna dict con correcciones aplicadas (vacío si no hay diferencias).
    """
    fecha = db_p.get("fecha")
    if not fecha:
        return {}

    date_str = fecha.strftime("%Y%m%d") if hasattr(fecha, "strftime") else str(fecha)[:10].replace("-", "")
    if date_str not in espn_cache:
        # Fallback: si el scoreboard no fue pre-cargado (no debería pasar en sync_torneo
        # porque se pre-carga antes del gather, pero puede ocurrir en llamadas directas).
        espn_cache[date_str] = await _espn_scoreboard(client, fecha)

    events = espn_cache[date_str]
    if not events:
        return {}

    local    = db_p.get("local_nombre", "")
    visitante = db_p.get("visit_nombre", "")
    game_id = _espn_find_game_id(events, local, visitante)
    if not game_id:
        logger.info(f"  ESPN: partido no encontrado en scoreboard — {local} vs {visitante} ({date_str})")
        return {}

    summary = await _espn_get_summary(client, game_id)
    if not summary:
        return {}

    espn = _espn_extract_stats(summary)

    # Guardar valores crudos ESPN para la tabla de auditoría (si se pide)
    if out_raw is not None:
        out_raw["amarillas"]       = espn.get("amarillas", 0)
        out_raw["rojas"]           = espn.get("rojas", 0)
        out_raw["decisiones_var"]  = espn.get("decisiones_var", 0)
        out_raw["penales_partido"] = espn.get("penales_partido", 0)

    # Leer valores actuales del partido en BD (post API-Football update)
    rq = await db.execute(
        text("""SELECT decisiones_var, amarillas, rojas, minuto_primer_gol,
                       penales_partido, penales_local, penales_visitante
                FROM partido WHERE id = :pid"""),
        {"pid": partido_id},
    )
    current = dict(rq.mappings().first() or {})

    corrections: dict = {}

    # J / K / L: lógica unificada — ESPN como fallback SOLO cuando API devuelve 0.
    # Si API tiene > 0 no se pisa. Si API tiene 0 y ESPN > 0, se adopta ESPN.
    # (API-Football events son más precisos cuando los tiene; ESPN sobrecontea VAR
    #  y puede incluir la 2ª amarilla como amarilla. Solo usamos ESPN de rescate.)
    espn_var  = espn.get("decisiones_var", 0)
    espn_amar = espn.get("amarillas",      0)
    espn_roja = espn.get("rojas",          0)

    if (current.get("decisiones_var") or 0) == 0 and espn_var  > 0:
        corrections["decisiones_var"] = espn_var
    if (current.get("amarillas")      or 0) == 0 and espn_amar > 0:
        corrections["amarillas"]      = espn_amar
    if (current.get("rojas")          or 0) == 0 and espn_roja > 0:
        corrections["rojas"]          = espn_roja

    # Minuto primer gol: ESPN solo como fallback (API-Football es más preciso)
    if "minuto_primer_gol" in espn and not current.get("minuto_primer_gol"):
        corrections["minuto_primer_gol"] = espn["minuto_primer_gol"]

    # Penales durante el partido (item M): ESPN como fuente complementaria
    if "penales_partido" in espn and (espn["penales_partido"] or 0) > (current.get("penales_partido") or 0):
        corrections["penales_partido"] = espn["penales_partido"]

    # Tanda de penales (item O): ESPN si BD no tiene datos
    if "penales_local_tanda" in espn and current.get("penales_local") is None:
        corrections["penales_local"]    = espn["penales_local_tanda"]
        corrections["penales_visitante"] = espn.get("penales_visitante_tanda")

    if not corrections:
        logger.info(f"  ESPN ✓ sin diferencias — {local} vs {visitante}")
        return {}

    set_clauses = ", ".join(f"{k} = :{k}" for k in corrections)
    await db.execute(
        text(f"UPDATE partido SET {set_clauses} WHERE id = :pid"),
        {**corrections, "pid": partido_id},
    )
    logger.info(f"  ESPN 🔧 corregido partido_id={partido_id} ({local} vs {visitante}): {corrections}")
    return corrections


# ── SofaScore helpers ─────────────────────────────────────────────────────────

async def _sofascore_scoreboard(client: httpx.AsyncClient, fecha) -> list[dict]:
    """
    Retorna eventos de fútbol de SofaScore para una fecha dada.
    Endpoint: GET /sport/football/scheduled-events/{date} (formato YYYY-MM-DD)
    """
    if not SOFASCORE_ENABLED:
        return []
    if hasattr(fecha, "strftime"):
        date_str = fecha.strftime("%Y-%m-%d")
    else:
        date_str = str(fecha)[:10]
    try:
        r = await client.get(
            f"{SOFASCORE_BASE}/sport/football/scheduled-events/{date_str}",
            headers=SOFASCORE_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("events", [])
    except Exception as e:
        logger.warning(f"SofaScore scoreboard error ({date_str}): {e}")
        return []


def _sofascore_find_event(events: list[dict], local: str, visitante: str) -> int | None:
    """
    Busca el SofaScore event_id por nombres de equipos normalizados.
    Retorna el event_id (int) o None.
    Intenta match directo (local=home, visitante=away) e inverso (para KO).
    """
    loc_n = _normalize(local)
    vis_n = _normalize(visitante)
    if not loc_n or not vis_n:
        return None
    for ev in events:
        home = _normalize(ev.get("homeTeam", {}).get("name", ""))
        away = _normalize(ev.get("awayTeam", {}).get("name", ""))
        if not home or not away:
            continue
        match_dir = ((loc_n in home or home in loc_n) and
                     (vis_n in away  or away  in vis_n))
        match_inv = ((vis_n in home or home in vis_n) and
                     (loc_n in away  or away  in loc_n))
        if match_dir or match_inv:
            return ev.get("id")
    return None


async def _sofascore_get_incidents(client: httpx.AsyncClient, event_id: int) -> list[dict]:
    """
    Descarga los incidents de un evento SofaScore.
    Endpoint: GET /event/{id}/incidents
    """
    try:
        r = await client.get(
            f"{SOFASCORE_BASE}/event/{event_id}/incidents",
            headers=SOFASCORE_HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("incidents", [])
    except Exception as e:
        logger.warning(f"SofaScore incidents error (event_id={event_id}): {e}")
        return []


def _sofascore_extract_stats(incidents: list[dict]) -> dict:
    """
    Extrae estadísticas de tarjetas, VAR y penales desde incidents de SofaScore.

    Tipos de incident relevantes:
      incidentType='card', incidentClass='yellow'    → amarilla (1ª)
      incidentType='card', incidentClass='yellowRed' → 2ª amarilla = ROJA (expulsión)
      incidentType='card', incidentClass='red'       → roja directa
      incidentType='varDecision'                     → decisión VAR (1 evento = 1 decisión)
      incidentType='goal',  incidentClass='penalty'  → penal convertido (item M)
      incidentType='missedPenalty'                   → penal fallado/atajado (item M)

    Retorna: {amarillas, rojas, decisiones_var, penales_partido, minuto_primer_gol?}
    """
    amarillas = 0
    rojas = 0
    decisiones_var = 0
    penales_partido = 0  # item M: penales cobrados durante el partido (no tanda)
    first_goal_min: int | None = None

    # Excluir incidents de tanda de penales (periodo shootout)
    # SofaScore usa period.value: 1=1T, 2=2T, 3=ET1, 4=ET2, 5=shootout
    _SHOOTOUT_PERIODS = {5, "5", "penalties"}

    for inc in incidents:
        inc_type = inc.get("incidentType", "")
        inc_class = inc.get("incidentClass", "")
        period = inc.get("period", {})
        period_val = period.get("value") if isinstance(period, dict) else period

        # Ignorar incidents de tanda de penales
        if period_val in _SHOOTOUT_PERIODS:
            continue

        if inc_type == "card":
            if inc_class == "yellow":
                amarillas += 1
            elif inc_class in ("yellowRed", "red"):
                # yellowRed = 2ª amarilla → cuenta como roja (expulsión)
                # red = roja directa
                rojas += 1
        elif inc_type == "varDecision":
            # Cada evento varDecision = 1 decisión VAR real
            decisiones_var += 1
        elif inc_type == "goal" and inc_class == "penalty":
            # Penal convertido durante el partido (no tanda)
            penales_partido += 1
            # También podría ser el primer gol del partido
            if first_goal_min is None:
                try:
                    first_goal_min = int(inc.get("time", 0) or 0) or None
                except (TypeError, ValueError):
                    pass
        elif inc_type == "missedPenalty":
            # Penal fallado o atajado durante el partido (no tanda)
            penales_partido += 1
        elif inc_type == "goal":
            # Gol normal — capturar minuto del primer gol
            if first_goal_min is None:
                try:
                    first_goal_min = int(inc.get("time", 0) or 0) or None
                except (TypeError, ValueError):
                    pass

    result = {
        "amarillas": amarillas,
        "rojas": rojas,
        "decisiones_var": decisiones_var,
        "penales_partido": penales_partido,
    }
    if first_goal_min is not None:
        result["minuto_primer_gol"] = first_goal_min
    return result


async def _sofascore_verify_and_patch(
    db: AsyncSession,
    client: httpx.AsyncClient,
    db_p: dict,
    partido_id: int,
    ss_cache: dict,
    api_vals: dict | None = None,
    espn_raw: dict | None = None,
    estado_partido: str = "finalizado",
    minuto_actual: int | None = None,
    force: bool = False,
) -> dict:
    """
    Verifica y corrige tarjetas, VAR y penales usando SofaScore.

    Nueva lógica (sesión 39):
    - SofaScore corrige SOLO si su valor es MAYOR que el ya aplicado (API+ESPN).
    - estado_partido: 'finalizado' | 'live' | 'pendiente' — se persiste en partido_stats_fuentes.
    - minuto_actual: minuto de juego actual (para live tracking, se guarda en ultimo_minuto).
    - Para 'finalizado': skip si ya existe una fila con estado='finalizado' → no re-procesar.
      Con force=True se omite el skip y se re-procesa siempre.
    - Siempre hace UPSERT en partido_stats_fuentes.

    api_vals: valores crudos API-Football (Fase B). espn_raw: valores crudos ESPN (Fase C).
    """
    fecha = db_p.get("fecha")
    if not fecha:
        return {}

    # Para finalizados: skip si ya fue procesado completamente (salvo force=True)
    if estado_partido == "finalizado" and not force:
        try:
            ck = await db.execute(
                text("SELECT estado FROM partido_stats_fuentes WHERE partido_id = :pid"),
                {"pid": partido_id},
            )
            existing = ck.mappings().first()
            if existing and existing.get("estado") == "finalizado":
                logger.info(f"  partido_stats_fuentes: partido {partido_id} ya finalizado, skip")
                return {}
        except Exception:
            pass

    date_str = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)[:10]
    if date_str not in ss_cache:
        ss_cache[date_str] = await _sofascore_scoreboard(client, fecha)

    events = ss_cache.get(date_str, [])

    local     = db_p.get("local_nombre", "")
    visitante = db_p.get("visit_nombre", "")

    ss: dict = {}
    if events:
        event_id = _sofascore_find_event(events, local, visitante)
        if event_id:
            incidents = await _sofascore_get_incidents(client, event_id)
            if incidents:
                ss = _sofascore_extract_stats(incidents)
            else:
                logger.info(f"  SofaScore: sin incidents — {local} vs {visitante}")
        else:
            logger.info(f"  SofaScore: partido no encontrado — {local} vs {visitante} ({date_str})")
    else:
        logger.info(f"  SofaScore: sin eventos para fecha {date_str}")

    # Leer valores actuales en BD (post API-Football + ESPN = el "máximo previo")
    rq = await db.execute(
        text("""SELECT decisiones_var, amarillas, rojas, penales_partido
                FROM partido WHERE id = :pid"""),
        {"pid": partido_id},
    )
    current = dict(rq.mappings().first() or {})

    cur_amar  = current.get("amarillas")       or 0
    cur_rojas = current.get("rojas")            or 0
    cur_var   = current.get("decisiones_var")   or 0
    cur_pp    = current.get("penales_partido")  or 0

    ss_amar   = ss.get("amarillas", 0)       if ss else 0
    ss_rojas  = ss.get("rojas", 0)           if ss else 0
    ss_var    = ss.get("decisiones_var", 0)  if ss else 0
    ss_pp     = ss.get("penales_partido", 0) if ss else 0

    corrections: dict = {}

    # SofaScore solo corrige si da un valor MAYOR que el ya aplicado (API+ESPN)
    if ss_amar > cur_amar:
        corrections["amarillas"] = ss_amar
        logger.info(f"  SofaScore J: {local} vs {visitante} — amarillas {cur_amar} → {ss_amar} ✓ (mayor)")
    elif ss and ss_amar < cur_amar:
        logger.info(f"  SofaScore J: {local} vs {visitante} — SS={ss_amar} < actual={cur_amar}, mantiene API/ESPN")

    if ss_rojas > cur_rojas:
        corrections["rojas"] = ss_rojas
        logger.info(f"  SofaScore K: {local} vs {visitante} — rojas {cur_rojas} → {ss_rojas} ✓ (mayor)")
    elif ss and ss_rojas < cur_rojas:
        logger.info(f"  SofaScore K: {local} vs {visitante} — SS={ss_rojas} < actual={cur_rojas}, mantiene API/ESPN")

    if ss_var > cur_var:
        corrections["decisiones_var"] = ss_var
        logger.info(f"  SofaScore L: {local} vs {visitante} — var {cur_var} → {ss_var} ✓ (mayor)")
    elif ss and ss_var < cur_var:
        logger.info(f"  SofaScore L: {local} vs {visitante} — SS={ss_var} < actual={cur_var}, mantiene API/ESPN")

    if ss_pp > cur_pp:
        corrections["penales_partido"] = ss_pp
        logger.info(f"  SofaScore M: {local} vs {visitante} — penales_partido {cur_pp} → {ss_pp} ✓ (mayor)")
    elif ss and ss_pp < cur_pp:
        logger.info(f"  SofaScore M: {local} vs {visitante} — SS={ss_pp} < actual={cur_pp}, mantiene API/ESPN")

    if corrections:
        set_clauses = ", ".join(f"{k} = :{k}" for k in corrections)
        await db.execute(
            text(f"UPDATE partido SET {set_clauses} WHERE id = :pid"),
            {**corrections, "pid": partido_id},
        )
        logger.info(f"  SofaScore 🔧 corregido partido_id={partido_id} ({local} vs {visitante}): {corrections}")
    else:
        if ss:
            logger.info(f"  SofaScore ✓ sin correcciones (API/ESPN >= SS) — {local} vs {visitante}")

    # Valores finales en BD después de todas las fases
    final_amar  = corrections.get("amarillas",      cur_amar)
    final_rojas = corrections.get("rojas",           cur_rojas)
    final_var   = corrections.get("decisiones_var",  cur_var)
    final_pp    = corrections.get("penales_partido", cur_pp)

    # Determinar qué fuente ganó para cada campo
    api_a  = (api_vals or {}).get("amarillas",       cur_amar)
    api_r  = (api_vals or {}).get("rojas",            cur_rojas)
    api_v  = (api_vals or {}).get("decisiones_var",   cur_var)
    api_p  = (api_vals or {}).get("penales_partido",  cur_pp)
    espn_a = (espn_raw or {}).get("amarillas",        0)
    espn_r = (espn_raw or {}).get("rojas",            0)
    espn_v = (espn_raw or {}).get("decisiones_var",   0)
    espn_p = (espn_raw or {}).get("penales_partido",  0)

    def _fuente(api_v_: int, espn_v_: int, ss_v_: int, final_v_: int) -> str:
        if final_v_ == ss_v_ and ss_v_ > 0 and ss_v_ >= api_v_ and ss_v_ >= espn_v_:
            return "sofascore"
        if final_v_ == espn_v_ and espn_v_ > 0 and espn_v_ >= api_v_:
            return "espn"
        if api_v_ > 0:
            return "api"
        return "igual"

    fuente_a = _fuente(api_a, espn_a, ss_amar,  final_amar)
    fuente_r = _fuente(api_r, espn_r, ss_rojas, final_rojas)
    fuente_v = _fuente(api_v, espn_v, ss_var,   final_var)
    fuente_p = _fuente(api_p, espn_p, ss_pp,    final_pp)

    # UPSERT en tabla de auditoría de fuentes
    try:
        fecha_date     = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)[:10]
        torneo_id_aux  = db_p.get("torneo_id")
        numero_fifa_aux = db_p.get("numero_fifa")
        await db.execute(text("SAVEPOINT _sf_upsert_sp"))
        await db.execute(
            text("""
                INSERT INTO partido_stats_fuentes (
                    partido_id, torneo_id, numero_fifa, fecha, local, visitante,
                    api_amarillas, api_rojas, api_var, api_penales,
                    espn_amarillas, espn_rojas, espn_var, espn_penales,
                    ss_amarillas, ss_rojas, ss_var, ss_penales,
                    final_amarillas, final_rojas, final_var, final_penales,
                    fuente_amarillas, fuente_rojas, fuente_var, fuente_penales,
                    estado, ultimo_minuto, fuentes_run_at, synced_at
                ) VALUES (
                    :pid, :tid, :num_fifa, :fecha, :local, :visit,
                    :api_a, :api_r, :api_v, :api_p,
                    :espn_a, :espn_r, :espn_v, :espn_p,
                    :ss_a, :ss_r, :ss_v, :ss_p,
                    :fin_a, :fin_r, :fin_v, :fin_p,
                    :f_a, :f_r, :f_v, :f_p,
                    :estado, :ult_min, NOW(), NOW()
                )
                ON CONFLICT (partido_id) DO UPDATE SET
                    torneo_id        = EXCLUDED.torneo_id,
                    numero_fifa      = EXCLUDED.numero_fifa,
                    fecha            = EXCLUDED.fecha,
                    local            = EXCLUDED.local,
                    visitante        = EXCLUDED.visitante,
                    api_amarillas    = EXCLUDED.api_amarillas,
                    api_rojas        = EXCLUDED.api_rojas,
                    api_var          = EXCLUDED.api_var,
                    api_penales      = EXCLUDED.api_penales,
                    espn_amarillas   = EXCLUDED.espn_amarillas,
                    espn_rojas       = EXCLUDED.espn_rojas,
                    espn_var         = EXCLUDED.espn_var,
                    espn_penales     = EXCLUDED.espn_penales,
                    ss_amarillas     = EXCLUDED.ss_amarillas,
                    ss_rojas         = EXCLUDED.ss_rojas,
                    ss_var           = EXCLUDED.ss_var,
                    ss_penales       = EXCLUDED.ss_penales,
                    final_amarillas  = EXCLUDED.final_amarillas,
                    final_rojas      = EXCLUDED.final_rojas,
                    final_var        = EXCLUDED.final_var,
                    final_penales    = EXCLUDED.final_penales,
                    fuente_amarillas = EXCLUDED.fuente_amarillas,
                    fuente_rojas     = EXCLUDED.fuente_rojas,
                    fuente_var       = EXCLUDED.fuente_var,
                    fuente_penales   = EXCLUDED.fuente_penales,
                    -- No hacer downgrade: finalizado nunca retrocede a live/pendiente
                    estado           = CASE
                        WHEN partido_stats_fuentes.estado = 'finalizado'
                        THEN 'finalizado'
                        ELSE EXCLUDED.estado
                    END,
                    ultimo_minuto    = EXCLUDED.ultimo_minuto,
                    fuentes_run_at   = NOW(),
                    synced_at        = NOW()
            """),
            {
                "pid": partido_id, "tid": torneo_id_aux, "num_fifa": numero_fifa_aux,
                "fecha": fecha_date, "local": local, "visit": visitante,
                "api_a": api_a if api_vals else None,
                "api_r": api_r if api_vals else None,
                "api_v": api_v if api_vals else None,
                "api_p": api_p if api_vals else None,
                "espn_a": espn_a if espn_raw else None,
                "espn_r": espn_r if espn_raw else None,
                "espn_v": espn_v if espn_raw else None,
                "espn_p": espn_p if espn_raw else None,
                "ss_a": ss_amar  if ss else None,
                "ss_r": ss_rojas if ss else None,
                "ss_v": ss_var   if ss else None,
                "ss_p": ss_pp    if ss else None,
                "fin_a": final_amar, "fin_r": final_rojas,
                "fin_v": final_var,  "fin_p": final_pp,
                "f_a": fuente_a, "f_r": fuente_r,
                "f_v": fuente_v, "f_p": fuente_p,
                "estado":  estado_partido,
                "ult_min": minuto_actual,
            },
        )
        await db.execute(text("RELEASE SAVEPOINT _sf_upsert_sp"))
    except Exception as e:
        try:
            await db.execute(text("ROLLBACK TO SAVEPOINT _sf_upsert_sp"))
        except Exception:
            pass
        logger.warning(f"  partido_stats_fuentes UPSERT error partido {partido_id}: {e}")
        print(f"  [DIAG] UPSERT error partido {partido_id}: {e}", flush=True)

    return corrections


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
    fecha_filtro=None,   # date | None — si se provee, solo sincroniza partidos de esa fecha
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

        # Detectar partidos KO activos sin mapear (equipos definidos, no TBD, no finalizados)
        r_unmapped = await db.execute(
            text("""
                SELECT COUNT(*) FROM partido p
                JOIN fase f ON f.id = p.fase_id
                WHERE p.torneo_id = :tid
                  AND p.api_fixture_id IS NULL
                  AND p.estado NOT IN ('finalizado')
                  AND p.equipo_local_id IS NOT NULL
                  AND p.equipo_visitante_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM equipo WHERE id = p.equipo_local_id AND nombre = 'TBD'
                  )
                  AND NOT EXISTS (
                      SELECT 1 FROM equipo WHERE id = p.equipo_visitante_id AND nombre = 'TBD'
                  )
            """),
            {"tid": torneo_id},
        )
        unmapped_active = r_unmapped.scalar() or 0

        if fixtures_mapeados == 0 or unmapped_active > 0:
            # También verificar/auto-detectar api_league_id y api_season
            mapeo_summary = await auto_mapeo_torneo(db, torneo_id, _client_check)
            if not mapeo_summary.get("auto_mapeo"):
                if fixtures_mapeados == 0:
                    # Sin ningún fixture mapeado y auto-mapeo falló: no podemos continuar
                    return {
                        "ok": False,
                        "actualizados": 0,
                        "auto_mapeo": mapeo_summary,
                        "error": mapeo_summary.get("error", "No se pudo auto-mapear"),
                    }
                # Si ya hay fixtures mapeados (grupos), continuar igual aunque falle el re-mapeo KO
                mapeo_summary = {"auto_mapeo": False, "warn": "Re-mapeo KO falló; sincronizando con fixtures existentes"}
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
    # Garantizar que datos_confirmados existe (idempotente — no falla si ya existe)
    try:
        await db.execute(text(
            "ALTER TABLE partido ADD COLUMN IF NOT EXISTS "
            "datos_confirmados BOOLEAN DEFAULT FALSE"
        ))
        await db.commit()
    except Exception:
        await db.rollback()

    _ff_extra = "AND DATE(p.fecha AT TIME ZONE 'UTC') = :ffecha" if fecha_filtro else ""
    _ff_params = {"ffecha": fecha_filtro} if fecha_filtro else {}
    _sql2 = (
        "SELECT p.id, p.api_fixture_id, p.estado,"
        " p.torneo_id, p.numero_fifa,"
        " p.equipo_local_id, p.equipo_visitante_id,"
        " COALESCE(el.nombre_es, el.nombre, '?') AS local_nombre,"
        " COALESCE(ev.nombre_es, ev.nombre, '?') AS visit_nombre,"
        " p.fecha,"
        " COALESCE(p.datos_confirmados, FALSE) AS datos_confirmados"
        " FROM partido p"
        " LEFT JOIN equipo el ON el.id = p.equipo_local_id"
        " LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id"
        " WHERE p.torneo_id = :tid AND p.api_fixture_id IS NOT NULL"
        + (" " + _ff_extra if _ff_extra else "")
    )
    r2 = await db.execute(
        text(_sql2),
        {"tid": torneo_id, **_ff_params},
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
    espn_corrections: list = []   # correcciones ESPN — inicializado antes del async with
    ss_corrections: list = []     # correcciones SofaScore — inicializado antes del async with
    to_detail: list = []          # partidos a actualizar — inicializado antes del async with

    LIVE_STATUSES = {"1H", "HT", "2H", "ET", "BT", "P", "LIVE"}

    # ── Incremental pre-check: si todos los partidos DB ya están finalizados,
    #    no hace falta ninguna llamada a API-Football. ──────────────────────────
    if not force:
        now_utc_pre = datetime.now(timezone.utc)
        pending_fix_ids: set[int] = set()
        for fix_id, db_p in db_partidos.items():
            # ── Partidos confirmados: nunca se actualizan con sync ──────────────
            if db_p.get("datos_confirmados"):
                continue
            if db_p["estado"] != "finalizado":
                pending_fix_ids.add(fix_id)
                continue
            # Aunque esté "finalizado" en BD, incluir si está en ventana temporal
            # (por si el estado BD está desactualizado — muy raro pero defensivo)
            fecha = db_p.get("fecha")
            if fecha:
                try:
                    if hasattr(fecha, "tzinfo") and fecha.tzinfo:
                        elapsed = (now_utc_pre - fecha).total_seconds() / 60
                    else:
                        elapsed = (datetime.utcnow() - fecha).total_seconds() / 60
                    if 0.0 <= elapsed <= 300.0:   # ventana 5h
                        pending_fix_ids.add(fix_id)
                except Exception:
                    pass

        if not pending_fix_ids:
            logger.info(
                f"Incremental skip: todos los {len(db_partidos)} partidos ya finalizados "
                f"— 0 llamadas API-Football"
            )
            return {
                "ok": True,
                "actualizados": 0,
                "ya_finalizados": [db_p["id"] for db_p in db_partidos.values()],
                "sin_match": [],
                "api_calls": 0,
                "errores": [],
                "ids_actualizados": [],
                "ids_errores": [],
                "auto_mapeo": mapeo_summary,
                "msg": "Incremental: sin partidos pendientes — 0 llamadas API",
            }

        logger.info(
            f"Incremental: {len(pending_fix_ids)} partido(s) pendientes de {len(db_partidos)} totales"
        )
    else:
        pending_fix_ids = set(db_partidos.keys())

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
            # Partidos con datos confirmados: no tocar
            if db_p.get("datos_confirmados"):
                ya_finalizados.append(db_p["id"])
                continue
            # Incremental: saltar si ya estaba finalizado Y no estaba en pending_fix_ids
            if fix_id not in pending_fix_ids:
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
            # Partidos con datos confirmados: no tocar (ni en vivo)
            if db_p.get("datos_confirmados"):
                ya_finalizados.append(db_p["id"])
                continue
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
        # Fase A: fetch HTTP en PARALELO (todas las llamadas simultáneas).
        # Fase B: escritura a BD en secuencial (una sesión asyncpg no soporta concurrencia).
        all_finished = finished_fixtures
        detalle_count = 0
        espn_cache: dict = {}
        espn_corrections: list = []

        # Separar los que van a detalle vs los que van a básico
        to_fetch_detail = []
        to_basic_only   = []
        for fix_id, db_p, is_live in to_detail:
            if is_live or detalle_count < max_detalle:
                to_fetch_detail.append((fix_id, db_p, is_live))
                detalle_count += 1
            else:
                to_basic_only.append((fix_id, db_p, is_live))

        # Básicos sin call individual
        for fix_id, db_p, is_live in to_basic_only:
            match_name = f"{db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"
            logger.info(f"  Límite max_detalle={max_detalle} alcanzado; básico para {match_name}")
            fix_basic = next((f for f in all_finished if f["fixture"]["id"] == fix_id), None)
            if fix_basic:
                try:
                    await _update_partido_basic(db, db_p["id"], fix_basic, team_id_map)
                    actualizados.append(db_p["id"])
                except Exception as e:
                    errores.append({"partido_id": db_p["id"], "error": str(e)})

        # Fase A: fetch en paralelo
        async def _fetch_one(fix_id: int, db_p: dict, is_live: bool):
            tag = "🔴 LIVE" if is_live else "FT"
            match_name = f"{db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"
            t0 = time.time()
            try:
                resp = await client.get(
                    f"{API_BASE}/fixtures", params={"id": fix_id}, headers=_headers()
                )
                resp.raise_for_status()
                elapsed = time.time() - t0
                logger.info(f"  Fetch [{tag}] {match_name} OK ({elapsed:.1f}s)")
                return fix_id, db_p, is_live, resp, t0, None
            except Exception as e:
                elapsed = time.time() - t0
                logger.warning(f"  Fetch [{tag}] {match_name} ERROR ({elapsed:.1f}s): {e}")
                return fix_id, db_p, is_live, None, t0, str(e)

        import asyncio as _asyncio
        fetch_results = await _asyncio.gather(
            *[_fetch_one(fix_id, db_p, is_live) for fix_id, db_p, is_live in to_fetch_detail]
        )
        api_calls += sum(1 for r in fetch_results if r[3] is not None)

        # Fase B: log + update DB secuencial
        finished_to_espn = []
        api_vals_map: dict[int, dict] = {}   # partido_id → valores crudos API-Football
        for fix_id, db_p, is_live, resp, t0, err in fetch_results:
            partido_id = db_p["id"]
            match_name = f"{db_p.get('local_nombre','?')} vs {db_p.get('visit_nombre','?')}"

            if err:
                await _log(db, "/fixtures", {"id": fix_id}, None, t0,
                           error=err, contexto=match_name)
                errores.append({"partido_id": partido_id, "error": f"fetch individual: {err}"})
                continue

            await _log(db, "/fixtures", {"id": fix_id}, resp, t0, contexto=match_name)
            fixtures_resp = resp.json().get("response", [])
            if not fixtures_resp:
                errores.append({"partido_id": partido_id, "error": "respuesta vacía"})
                continue

            fix_full = fixtures_resp[0]
            try:
                api_raw = await _update_partido_full(db, partido_id, fix_full, team_id_map)
                await db.commit()
                api_vals_map[partido_id] = api_raw
                actualizados.append(partido_id)
                logger.info(f"  ✓ Actualizado: {match_name} (partido_id={partido_id})")
                fix_status = fix_full.get("fixture", {}).get("status", {}).get("short", "")
                if fix_status in STATUS_FINAL:
                    finished_to_espn.append((partido_id, db_p))
            except Exception as e:
                await db.rollback()
                errores.append({"partido_id": partido_id, "error": str(e)})
                logger.warning(f"  ✗ Error actualizando {match_name}: {e}")

        # Fase C: ESPN verify en paralelo (scoreboard cacheado por fecha)
        # ESPN: usado solo para minuto_primer_gol, penales tanda y penales partido (fallback).
        # Para tarjetas y VAR: solo como fallback cuando API-Football no tiene datos (=0).
        espn_raw_map: dict[int, dict] = {}   # partido_id → valores crudos ESPN
        if finished_to_espn:
            # Pre-cargar scoreboards ESPN de forma garantizada (1 call por fecha).
            # IMPORTANTE: hacerlo secuencialmente ANTES del gather para evitar race
            # condition cuando partidos simultáneos comparten la misma fecha.
            fechas_unicas: dict[str, object] = {}   # ds → fecha_obj (primero ganador)
            for _pid, _dbp in finished_to_espn:
                _f = _dbp.get("fecha")
                if _f:
                    ds = _f.strftime("%Y%m%d") if hasattr(_f, "strftime") else str(_f)[:10].replace("-", "")
                    if ds not in fechas_unicas:
                        fechas_unicas[ds] = _f
            for ds, fecha_obj in fechas_unicas.items():
                if ds not in espn_cache:
                    espn_cache[ds] = await _espn_scoreboard(client, fecha_obj)
                    logger.info(f"  ESPN scoreboard pre-cargado: {ds} ({len(espn_cache[ds])} eventos)")

            # Los summary ESPN (por partido) sí pueden ir en paralelo — son calls
            # independientes por game_id, el cache de scoreboard ya está listo.
            async def _espn_one(partido_id, db_p):
                out_raw: dict = {}
                try:
                    corr = await _espn_verify_and_patch(
                        db, client, db_p, partido_id, espn_cache, out_raw=out_raw
                    )
                    return partido_id, corr, out_raw
                except Exception as e:
                    logger.warning(f"  ESPN verify error partido {partido_id}: {e}")
                    return partido_id, {}, out_raw

            espn_results = await _asyncio.gather(
                *[_espn_one(pid, dbp) for pid, dbp in finished_to_espn]
            )
            # Commit secuencial post-gather (sin race condition)
            for pid, corr, raw in espn_results:
                if raw:
                    espn_raw_map[pid] = raw
                if corr:
                    await db.commit()
                    espn_corrections.append({"partido_id": pid, "corr": corr})

        # Fase D: SofaScore verify en paralelo.
        # Nueva lógica: SofaScore solo corrige si su valor es MAYOR que el actual (API+ESPN).
        # SofaScore distingue correctamente 1ª amarilla de 2ª amarilla (expulsión),
        # y reporta VAR como eventos discretos (sin sobreconteo de commentary).
        # También hace UPSERT en partido_stats_fuentes para auditoría.
        ss_cache: dict = {}
        ss_corrections: list = []
        if finished_to_espn:
            async def _ss_one(partido_id, db_p):
                try:
                    corr = await _sofascore_verify_and_patch(
                        db, client, db_p, partido_id, ss_cache,
                        api_vals=api_vals_map.get(partido_id),
                        espn_raw=espn_raw_map.get(partido_id),
                    )
                    return partido_id, corr
                except Exception as e:
                    logger.warning(f"  SofaScore verify error partido {partido_id}: {e}")
                    return partido_id, {}

            ss_results = await _asyncio.gather(
                *[_ss_one(pid, dbp) for pid, dbp in finished_to_espn]
            )
            for pid, corr in ss_results:
                if corr:
                    await db.commit()
                    ss_corrections.append({"partido_id": pid, "corr": corr})

        # Fase E: Inicializar filas pendientes y procesar transiciones live/pending.
        # Corre en cada sync para detectar cambios de estado sin gastar cuota API-Football.
        try:
            await _init_stats_fuentes_pending(db, torneo_id)
            live_pending_result = await _process_live_pending_updates(
                db, client, torneo_id, ss_cache, espn_cache,
            )
            if live_pending_result.get("actualizados", 0) > 0:
                await _log_warn(
                    db,
                    f"📡 live/pending actualizados: {live_pending_result['actualizados']} partido(s)"
                )
        except Exception as _e_fase_e:
            logger.warning(f"  Fase E (live/pending tracking) error: {_e_fase_e}")

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
    if espn_corrections:
        espn_ids = [c["partido_id"] for c in espn_corrections]
        await _log_warn(db, f"ESPN correcciones: {len(espn_corrections)} partidos {espn_ids}")
    if ss_corrections:
        ss_ids = [c["partido_id"] for c in ss_corrections]
        await _log_warn(db, f"SofaScore correcciones: {len(ss_corrections)} partidos {ss_ids}")

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
        "espn_correcciones": espn_corrections,
        "sofascore_correcciones": ss_corrections,
        **({"auto_mapeo": mapeo_summary} if mapeo_summary else {}),
    }

# ── Live/Pending tracking para partido_stats_fuentes ────────────────────────

async def _init_stats_fuentes_pending(
    db: AsyncSession,
    torneo_id: int,
) -> int:
    """
    Inicializa filas en partido_stats_fuentes para todos los partidos del torneo
    que aún NO tienen fila (estado pendiente o live).
    No sobrescribe filas existentes.
    Retorna cantidad de filas creadas.
    """
    try:
        tid = int(torneo_id)
        rq = await db.execute(
            text(f"""
                INSERT INTO partido_stats_fuentes (partido_id, torneo_id, numero_fifa, fecha, local, visitante, estado)
                SELECT
                    p.id,
                    {tid},
                    p.numero_fifa::TEXT,
                    DATE(p.fecha),
                    COALESCE(el.nombre_es, el.nombre, '?'),
                    COALESCE(ev.nombre_es, ev.nombre, '?'),
                    CASE
                        WHEN p.estado = 'finalizado' THEN 'finalizado'
                        WHEN p.estado = 'en_juego'   THEN 'live'
                        ELSE 'pendiente'
                    END
                FROM partido p
                LEFT JOIN equipo el ON el.id = p.equipo_local_id
                LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE p.torneo_id = {tid}
                  AND NOT EXISTS (
                      SELECT 1 FROM partido_stats_fuentes sf WHERE sf.partido_id = p.id
                  )
            """),
        )
        count = rq.rowcount or 0
        await db.commit()
        return count
    except Exception as e:
        await db.rollback()
        logger.warning(f"  _init_stats_fuentes_pending error: {e}")
        return 0


async def _process_live_pending_updates(
    db: AsyncSession,
    client: httpx.AsyncClient,
    torneo_id: int,
    ss_cache: dict,
    espn_cache: dict,
) -> dict:
    """
    Fase E del sync: procesa transiciones de estado y actualizaciones live.

    Para cada fila en partido_stats_fuentes con estado 'pendiente' o 'live':
      - pendiente → en_juego:   cambia a 'live', lanza ESPN+SS
      - pendiente → finalizado: cambia a 'finalizado', lanza ESPN+SS
      - live (minuto nuevo):    si partido.minuto_actual cambió, lanza ESPN+SS
      - live → finalizado:      cambia a 'finalizado', lanza ESPN+SS una vez

    Las consultas ESPN y SofaScore no consumen cuota de API-Football.
    Retorna resumen con conteo de actualizaciones.
    """
    try:
        rq = await db.execute(
            text("""
                SELECT sf.partido_id, sf.estado AS sf_estado, sf.ultimo_minuto,
                       p.estado AS p_estado, p.minuto_actual, p.fecha,
                       COALESCE(el.nombre_es, el.nombre, '?') AS local_nombre,
                       COALESCE(ev.nombre_es, ev.nombre, '?') AS visit_nombre
                FROM partido_stats_fuentes sf
                JOIN partido p ON p.id = sf.partido_id
                LEFT JOIN equipo el ON el.id = p.equipo_local_id
                LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
                WHERE sf.torneo_id = :tid
                  AND sf.estado IN ('pendiente', 'live')
            """),
            {"tid": torneo_id},
        )
        rows = list(rq.mappings())
    except Exception as e:
        logger.warning(f"  _process_live_pending: error leyendo tabla: {e}")
        return {"procesados": 0, "actualizados": 0, "errores": 0}

    if not rows:
        return {"procesados": 0, "actualizados": 0, "errores": 0}

    to_update: list[tuple] = []  # (partido_id, db_p, estado_target, minuto_target)

    for row in rows:
        sf_estado = row["sf_estado"]
        p_estado  = row["p_estado"]
        p_minuto  = row["minuto_actual"]
        sf_minuto = row["ultimo_minuto"]

        db_p = {
            "id":           row["partido_id"],
            "fecha":        row["fecha"],
            "local_nombre": row["local_nombre"],
            "visit_nombre": row["visit_nombre"],
            "torneo_id":    torneo_id,
        }

        if sf_estado == "pendiente":
            if p_estado == "en_juego":
                logger.info(f"  📡 pendiente→live: {row['local_nombre']} vs {row['visit_nombre']}")
                to_update.append((row["partido_id"], db_p, "live", p_minuto))
            elif p_estado == "finalizado":
                logger.info(f"  ✅ pendiente→finalizado: {row['local_nombre']} vs {row['visit_nombre']}")
                to_update.append((row["partido_id"], db_p, "finalizado", None))
            # Si sigue pendiente: solo actualizar estado en tabla (sin llamar fuentes)
            else:
                try:
                    await db.execute(text("SAVEPOINT _upd_pend_sp"))
                    await db.execute(
                        text("UPDATE partido_stats_fuentes SET synced_at=NOW() WHERE partido_id=:pid"),
                        {"pid": row["partido_id"]},
                    )
                    await db.execute(text("RELEASE SAVEPOINT _upd_pend_sp"))
                except Exception:
                    await db.execute(text("ROLLBACK TO SAVEPOINT _upd_pend_sp"))

        elif sf_estado == "live":
            if p_estado == "finalizado":
                logger.info(f"  ✅ live→finalizado: {row['local_nombre']} vs {row['visit_nombre']}")
                to_update.append((row["partido_id"], db_p, "finalizado", None))
            elif p_estado == "en_juego":
                # Solo actualizar si el minuto cambió
                if p_minuto is not None and p_minuto != sf_minuto:
                    logger.info(
                        f"  ⏱ live min {sf_minuto}→{p_minuto}: "
                        f"{row['local_nombre']} vs {row['visit_nombre']}"
                    )
                    to_update.append((row["partido_id"], db_p, "live", p_minuto))
                else:
                    logger.info(
                        f"  ⏱ live sin cambio (min={sf_minuto}): "
                        f"{row['local_nombre']} vs {row['visit_nombre']}"
                    )

    if not to_update:
        return {"procesados": len(rows), "actualizados": 0, "errores": 0}

    actualizados = 0
    errores = 0

    for pid, db_p, estado_target, minuto_target in to_update:
        try:
            local     = db_p["local_nombre"]
            visitante = db_p["visit_nombre"]
            fecha     = db_p.get("fecha")

            # ESPN raw (sin aplicar cambios a partido si es solo live check)
            espn_raw_e: dict = {}
            if fecha:
                ds = fecha.strftime("%Y%m%d") if hasattr(fecha, "strftime") else str(fecha)[:10].replace("-", "")
                if ds not in espn_cache:
                    espn_cache[ds] = await _espn_scoreboard(client, fecha)
                espn_evts = espn_cache.get(ds, [])
                if espn_evts:
                    gid = _espn_find_game_id(espn_evts, local, visitante)
                    if gid:
                        summary = await _espn_get_summary(client, gid)
                        if summary:
                            est = _espn_extract_stats(summary)
                            espn_raw_e = {
                                "amarillas":       est.get("amarillas",       0),
                                "rojas":           est.get("rojas",           0),
                                "decisiones_var":  est.get("decisiones_var",  0),
                                "penales_partido": est.get("penales_partido", 0),
                            }
                            # Aplicar correcciones ESPN al partido (fallback)
                            await _espn_verify_and_patch(db, client, db_p, pid, espn_cache)

            # SofaScore + UPSERT con nuevo estado
            await _sofascore_verify_and_patch(
                db, client, db_p, pid, ss_cache,
                api_vals=None,
                espn_raw=espn_raw_e or None,
                estado_partido=estado_target,
                minuto_actual=minuto_target,
            )
            await db.commit()
            actualizados += 1

        except Exception as e:
            await db.rollback()
            errores += 1
            logger.warning(f"  _process_live_pending: error partido {pid}: {e}")

    return {
        "procesados": len(rows),
        "actualizados": actualizados,
        "errores": errores,
    }


# ── Backfill tabla partido_stats_fuentes ────────────────────────────────────

async def populate_stats_fuentes_all(
    db: AsyncSession,
    torneo_id: int,
    client: httpx.AsyncClient,
) -> dict:
    """
    Pobla/actualiza partido_stats_fuentes para TODOS los partidos finalizados del torneo.

    Para cada partido:
    - Llama ESPN (scoreboard por fecha, cacheado) → obtiene valores crudos ESPN.
    - Llama SofaScore (incidents) → obtiene valores crudos SS.
    - Lee el valor actual en BD como "final" (ya tiene API+ESPN+SS merged).
    - Hace UPSERT en partido_stats_fuentes.
    - Aplica la nueva lógica "máximo": si SS > final, actualiza partido y tabla.

    No usa cuota de API-Football (solo ESPN y SofaScore).
    Retorna resumen: {procesados, corregidos_ss, errores, partidos}.
    """
    # 1. Inicializar filas pendientes para todos los partidos sin fila aún
    init_count = await _init_stats_fuentes_pending(db, torneo_id)
    if init_count:
        logger.info(f"  populate_stats_fuentes: {init_count} nuevas filas pendientes inicializadas")

    # 2. Obtener TODOS los partidos del torneo (sin filtrar por estado)
    tid = int(torneo_id)
    rq = await db.execute(
        text(f"""
            SELECT p.id, p.fecha, p.estado AS partido_estado,
                   COALESCE(el.nombre_es, el.nombre, 'Local') AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre, 'Visitante') AS visit_nombre,
                   p.amarillas, p.rojas, p.decisiones_var, p.penales_partido,
                   p.minuto_primer_gol, p.numero_fifa,
                   {tid} AS torneo_id
            FROM partido p
            LEFT JOIN equipo el ON el.id = p.equipo_local_id
            LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id = {tid}
            ORDER BY p.numero_fifa NULLS LAST, p.fecha
        """),
    )
    partidos = [dict(r) for r in rq.mappings().all()]

    if not partidos:
        return {
            "procesados": 0, "corregidos_ss": 0, "errores": 0,
            "partidos": [], "filas_inicializadas": init_count,
        }

    espn_cache: dict = {}
    ss_cache:   dict = {}
    procesados = 0
    corregidos  = 0
    errores     = 0
    resultado   = []

    for db_p in partidos:
        partido_id    = db_p["id"]
        local         = db_p.get("local_nombre", "")
        visitante     = db_p.get("visit_nombre", "")
        fecha         = db_p.get("fecha")
        estado_actual = db_p.get("partido_estado", "pendiente")

        # Mapear estado BD → estado tabla stats_fuentes
        if estado_actual == "finalizado":
            estado_sf = "finalizado"
        elif estado_actual == "en_juego":
            estado_sf = "live"
        else:
            estado_sf = "pendiente"

        try:
            # Valores actuales en partido (fuente de verdad para final_*)
            final_amar    = db_p.get("amarillas")         or 0
            final_rojas   = db_p.get("rojas")              or 0
            final_var     = db_p.get("decisiones_var")     or 0
            final_pp      = db_p.get("penales_partido")    or 0
            final_minuto  = db_p.get("minuto_primer_gol")  # puede ser NULL si no hubo gol

            # ESPN raw: solo si el partido tiene fecha (finalizado o en_juego)
            espn_amar = espn_rojas = espn_var = espn_pp = espn_minuto = None
            if fecha and estado_actual in ("finalizado", "en_juego"):
                ds = fecha.strftime("%Y%m%d") if hasattr(fecha, "strftime") else str(fecha)[:10].replace("-", "")
                if ds not in espn_cache:
                    espn_cache[ds] = await _espn_scoreboard(client, fecha)
                espn_events = espn_cache.get(ds, [])
                if espn_events:
                    game_id = _espn_find_game_id(espn_events, local, visitante)
                    if game_id:
                        summary = await _espn_get_summary(client, game_id)
                        if summary:
                            es = _espn_extract_stats(summary)
                            espn_amar   = es.get("amarillas",       0)
                            espn_rojas  = es.get("rojas",           0)
                            espn_var    = es.get("decisiones_var",  0)
                            espn_pp     = es.get("penales_partido", 0)
                            espn_minuto = es.get("minuto_primer_gol")  # puede ser None

            # SofaScore
            ss_amar = ss_rojas = ss_var = ss_pp = ss_minuto = None
            if fecha and estado_actual in ("finalizado", "en_juego"):
                date_str = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)[:10]
                if date_str not in ss_cache:
                    ss_cache[date_str] = await _sofascore_scoreboard(client, fecha)
                events = ss_cache.get(date_str, [])
                if events:
                    event_id = _sofascore_find_event(events, local, visitante)
                    if event_id:
                        incidents = await _sofascore_get_incidents(client, event_id)
                        if incidents:
                            ss = _sofascore_extract_stats(incidents)
                            ss_amar    = ss.get("amarillas",       0)
                            ss_rojas   = ss.get("rojas",           0)
                            ss_var     = ss.get("decisiones_var",  0)
                            ss_pp      = ss.get("penales_partido", 0)
                            ss_minuto  = ss.get("minuto_primer_gol")   # puede ser None

            # UPSERT directo — sin SAVEPOINT, sin lógica compleja
            # asyncpg necesita objeto date, no string
            from datetime import date as _date_cls
            if fecha is None:
                fecha_date = None
            elif hasattr(fecha, "date") and callable(fecha.date):
                fecha_date = fecha.date()   # datetime → date
            elif isinstance(fecha, _date_cls):
                fecha_date = fecha
            else:
                fecha_date = None

            # api_* = valores actuales en tabla partido (poblados por API-Football sync)
            api_amar   = final_amar    # partido.amarillas ya fue corregido post-ESPN/SS
            api_rojas  = final_rojas   # idem
            api_var    = final_var     # idem
            api_pp     = final_pp      # idem
            api_minuto = final_minuto  # idem (partido.minuto_primer_gol)

            await db.execute(
                text("""
                    INSERT INTO partido_stats_fuentes (
                        partido_id, torneo_id, numero_fifa, fecha, local, visitante,
                        api_amarillas,   api_rojas,   api_var,   api_penales,
                        espn_amarillas,  espn_rojas,  espn_var,  espn_penales,
                        ss_amarillas,    ss_rojas,    ss_var,    ss_penales,
                        final_amarillas, final_rojas, final_var, final_penales,
                        api_minuto,  espn_minuto,  ss_minuto,  minuto_primer_gol,
                        estado, fuentes_run_at, synced_at
                    ) VALUES (
                        :pid, :tid, :num_fifa, :fecha, :local, :visit,
                        :api_a,  :api_r,  :api_v,  :api_p,
                        :espn_a, :espn_r, :espn_v, :espn_p,
                        :ss_a,   :ss_r,   :ss_v,   :ss_p,
                        :fin_a,  :fin_r,  :fin_v,  :fin_p,
                        :api_min, :espn_min, :ss_min, :min_gol,
                        :estado, NOW(), NOW()
                    )
                    ON CONFLICT (partido_id) DO UPDATE SET
                        torneo_id          = EXCLUDED.torneo_id,
                        numero_fifa        = EXCLUDED.numero_fifa,
                        fecha              = EXCLUDED.fecha,
                        local              = EXCLUDED.local,
                        visitante          = EXCLUDED.visitante,
                        api_amarillas      = EXCLUDED.api_amarillas,
                        api_rojas          = EXCLUDED.api_rojas,
                        api_var            = EXCLUDED.api_var,
                        api_penales        = EXCLUDED.api_penales,
                        espn_amarillas     = EXCLUDED.espn_amarillas,
                        espn_rojas         = EXCLUDED.espn_rojas,
                        espn_var           = EXCLUDED.espn_var,
                        espn_penales       = EXCLUDED.espn_penales,
                        ss_amarillas       = EXCLUDED.ss_amarillas,
                        ss_rojas           = EXCLUDED.ss_rojas,
                        ss_var             = EXCLUDED.ss_var,
                        ss_penales         = EXCLUDED.ss_penales,
                        final_amarillas    = EXCLUDED.final_amarillas,
                        final_rojas        = EXCLUDED.final_rojas,
                        final_var          = EXCLUDED.final_var,
                        final_penales      = EXCLUDED.final_penales,
                        api_minuto         = EXCLUDED.api_minuto,
                        espn_minuto        = EXCLUDED.espn_minuto,
                        ss_minuto          = EXCLUDED.ss_minuto,
                        minuto_primer_gol  = EXCLUDED.minuto_primer_gol,
                        estado             = EXCLUDED.estado,
                        fuentes_run_at     = NOW(),
                        synced_at          = NOW()
                """),
                {
                    "pid": partido_id, "tid": tid,
                    "num_fifa": str(db_p.get("numero_fifa")) if db_p.get("numero_fifa") is not None else None,
                    "fecha": fecha_date, "local": local, "visit": visitante,
                    "api_a": api_amar, "api_r": api_rojas, "api_v": api_var, "api_p": api_pp,
                    "espn_a": espn_amar, "espn_r": espn_rojas, "espn_v": espn_var, "espn_p": espn_pp,
                    "ss_a": ss_amar, "ss_r": ss_rojas, "ss_v": ss_var, "ss_p": ss_pp,
                    "fin_a": final_amar, "fin_r": final_rojas, "fin_v": final_var, "fin_p": final_pp,
                    "api_min": api_minuto, "espn_min": espn_minuto, "ss_min": ss_minuto,
                    "min_gol": final_minuto,
                    "estado": estado_sf,
                },
            )
            await db.commit()
            corr = {}
            if ss_amar is not None or espn_amar is not None:
                corr = {"espn": espn_amar, "ss": ss_amar}
                corregidos += 1

            procesados += 1
            resultado.append({
                "partido_id": partido_id,
                "match": f"{local} vs {visitante}",
                "fecha": str(fecha)[:10] if fecha else None,
                "corregido": bool(corr),
                "corrections": corr,
            })

        except Exception as e:
            errores += 1
            logger.warning(f"  populate_stats_fuentes: error partido {partido_id} ({local} vs {visitante}): {e}")
            resultado.append({
                "partido_id": partido_id,
                "match": f"{local} vs {visitante}",
                "error": str(e),
            })

    return {
        "procesados": procesados,
        "corregidos_ss": corregidos,
        "errores": errores,
        "partidos": resultado,
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
) -> dict:
    """Actualiza un partido con datos completos (goals + events + statistics).
    Retorna los valores J/K/L/M extraídos por API-Football (antes de ESPN/SS)."""
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

    rojas_events    = 0  # fallback si statistics llegan tarde (partidos en vivo)
    amarillas_events = 0  # solo primeras amarillas (excluye 2ª amarilla=expulsión)
    # NOTA: la estadística "Yellow Cards" de API-Football incluye la 2ª amarilla
    # (que resulta en expulsión), inflando el total. Los eventos distinguen
    # "Yellow Card" (primera) de "Second Yellow card" (expulsión → roja).
    # Por eso usamos amarillas_events como fuente primaria para partidos finalizados.

    # Tarjetas POR EQUIPO (para fair play FIFA) — indexadas por api_team_id
    _local_api_id  = fix.get("teams", {}).get("home", {}).get("id")
    _away_api_id   = fix.get("teams", {}).get("away", {}).get("id")
    per_team_amar:  dict[int | None, int] = {_local_api_id: 0, _away_api_id: 0}
    per_team_rojas: dict[int | None, int] = {_local_api_id: 0, _away_api_id: 0}

    # Penales cobrados durante el partido (ítem M): convertidos + fallados.
    # NO incluye la tanda de penales (ítem O), que se cuenta aparte por score.penalty.
    penales_partido_total = 0

    # Rastrear goles anulados por VAR para no usarlos como minuto_primer_gol
    goles_anulados_minutos: set[int] = set()
    for ev in events_sorted:
        ev_type   = ev.get("type", "")
        ev_detail = ev.get("detail", "")
        elapsed   = ev.get("time", {}).get("elapsed")
        ev_team_id = ev.get("team", {}).get("id")

        if ev_type == "Var":
            var_count += 1
            # Si el VAR anula un gol, registrar el minuto para excluirlo
            if ev_detail in ("Goal Disallowed", "Goal Cancelled", "Offside Goal"):
                if elapsed is not None:
                    goles_anulados_minutos.add(elapsed)

        if ev_type == "Card":
            if ev_detail == "Yellow Card":
                amarillas_events += 1          # primera amarilla: cuenta como amarilla
                # Acumular por equipo para fair play
                if ev_team_id in per_team_amar:
                    per_team_amar[ev_team_id] += 1
            elif ev_detail in ("Red Card", "Second Yellow card"):
                rojas_events += 1              # roja directa o 2ª amarilla: cuenta como roja
                # Acumular por equipo para fair play
                if ev_team_id in per_team_rojas:
                    per_team_rojas[ev_team_id] += 1

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

    # decisiones_var: usar var_count SOLO si el fixture trajo eventos.
    # Si events estaba vacío (API no devolvió datos), pasar None para no pisar
    # un valor correcto ya guardado en BD (se usa COALESCE en el UPDATE).
    # Si events no estaba vacío pero var_count=0 → 0 es correcto (no hubo VAR).
    decisiones_var = var_count if events else None

    # Rojas: si los eventos capturaron más expulsiones que las estadísticas (partido en vivo
    # o stats incompletas), usar el conteo de eventos.
    if rojas_events > 0 and (rojas_total is None or rojas_total < rojas_events):
        rojas_total = rojas_events

    # Amarillas: preferir eventos sobre estadísticas para partidos finalizados.
    # Las stats de "Yellow Cards" incluyen la 2ª amarilla (que debería contarse como roja),
    # inflando el total. Los eventos son más precisos: "Yellow Card" = primera amarilla.
    if amarillas_events > 0:
        amarillas_total = amarillas_events  # más preciso: excluye 2ª amarilla

    elapsed_now = fix["fixture"]["status"].get("elapsed")

    # Para partidos finalizados: null → 0 SOLO si el fixture trajo datos para analizar.
    # Si tanto statistics como events están vacíos, la API no devolvió datos completos
    # → mantener None para que COALESCE preserve el valor ya guardado en BD.
    has_data = bool(fix.get("statistics")) or bool(events)
    STATUS_MAP_CHECK = {"FT", "AET", "PEN"}
    if status_short in STATUS_MAP_CHECK and has_data:
        if amarillas_total is None:
            amarillas_total = 0
        if rojas_total is None:
            rojas_total = 0
    # decisiones_var: None si sin eventos, int (0+) si con eventos (ya asignado arriba)
    # penales_partido: mismo criterio — None si sin eventos para no pisar valor correcto
    penales_partido_final = penales_partido_total if events else None

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

    # Tarjetas por equipo (fair play FIFA) — solo si los eventos las capturaron
    _loc_amar  = per_team_amar.get(_local_api_id)  if (events and _local_api_id) else None
    _vis_amar  = per_team_amar.get(_away_api_id)   if (events and _away_api_id)  else None
    _loc_rojas = per_team_rojas.get(_local_api_id) if (events and _local_api_id) else None
    _vis_rojas = per_team_rojas.get(_away_api_id)  if (events and _away_api_id)  else None

    # Guardar idempotente — ADD COLUMN IF NOT EXISTS (defensivo ante migraciones pendientes)
    try:
        await db.execute(text("""
            ALTER TABLE partido
                ADD COLUMN IF NOT EXISTS local_amarillas     INT,
                ADD COLUMN IF NOT EXISTS visitante_amarillas INT,
                ADD COLUMN IF NOT EXISTS local_rojas         INT,
                ADD COLUMN IF NOT EXISTS visitante_rojas     INT
        """))
    except Exception:
        pass

    await db.execute(
        text("""
            UPDATE partido SET
                goles_local            = :gl,
                goles_visitante        = :gv,
                penales_local          = :pl,
                penales_visitante      = :pv,
                estado                 = :est,
                minuto_actual          = :min_act,
                amarillas              = COALESCE(:am, amarillas),
                rojas                  = COALESCE(:ro, rojas),
                decisiones_var         = COALESCE(:dv, decisiones_var),
                minuto_primer_gol      = COALESCE(:mpg, minuto_primer_gol),
                equipo_clasificado_id  = COALESCE(:ecid, equipo_clasificado_id),
                penales_partido        = COALESCE(:pp, penales_partido),
                local_amarillas        = COALESCE(:loc_am,  local_amarillas),
                visitante_amarillas    = COALESCE(:vis_am,  visitante_amarillas),
                local_rojas            = COALESCE(:loc_ro,  local_rojas),
                visitante_rojas        = COALESCE(:vis_ro,  visitante_rojas)
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
            "pp":      penales_partido_final,
            "loc_am":  _loc_amar,
            "vis_am":  _vis_amar,
            "loc_ro":  _loc_rojas,
            "vis_ro":  _vis_rojas,
            "pid":     partido_id,
        },
    )
    await db.commit()
    # Retornar valores crudos de API-Football para la tabla de auditoría
    return {
        # None = sin datos (no pisamos BD); valor int = dato confirmado (0 incluido)
        "amarillas":       amarillas_total   if amarillas_total   is not None else 0,
        "rojas":           rojas_total       if rojas_total       is not None else 0,
        "decisiones_var":  decisiones_var    if decisiones_var    is not None else 0,
        "penales_partido": penales_partido_final if penales_partido_final is not None else 0,
        "_events_empty":   not events,   # True = fixture llegó sin eventos (diagnóstico)
    }
