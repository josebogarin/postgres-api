"""
Servicio de Torneos de Fútbol
─────────────────────────────
Usa API-Football (api-sports.io) para cargar fixture, resultados y estadísticas.

Configuración requerida en .env:
    APIFOOTBALL_KEY=tu_api_key_aqui
    APIFOOTBALL_HOST=v3.football.api-sports.io

API gratuita: 100 req/día — https://dashboard.api-football.com/register
"""

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings

log = logging.getLogger(__name__)

# ── Configuración API ──────────────────────────────────────────────────────────
API_BASE = "https://v3.football.api-sports.io"
API_KEY  = getattr(settings, "APIFOOTBALL_KEY", "")

# Ligas soportadas: id → (nombre_es, tipo, formato_playoff, emoji)
LIGAS_SOPORTADAS: dict[int, tuple] = {
    1:  ("Copa Mundial FIFA",        "paises", "partido_unico", "🌍"),
    2:  ("UEFA Champions League",    "clubes", "ida_vuelta",    "⭐"),
    4:  ("UEFA Eurocopa",            "paises", "partido_unico", "🏆"),
    9:  ("Copa América",             "paises", "partido_unico", "🏆"),
    13: ("Copa Libertadores",        "clubes", "ida_vuelta",    "🦅"),
}

# Mapeo tipo fase API-Football → tipo interno + orden
FASE_MAP: dict[str, tuple[str, int]] = {
    # Clasificatorias / previas  (orden < 10)
    "Qualifying Rounds":           ("clasificatoria",  2),
    "Preliminary Round":           ("clasificatoria",  2),
    "1st Qualifying Round":        ("clasificatoria",  3),
    "2nd Qualifying Round":        ("clasificatoria",  4),
    "3rd Qualifying Round":        ("clasificatoria",  5),
    "Play-offs":                   ("playoff_prev",    6),
    "Playoff Round":               ("playoff_prev",    6),
    # Fase de grupos  (orden 10)
    "Group Stage":                 ("grupo",          10),
    "Group Stage - 1":             ("grupo",          10),
    "Group Stage - 2":             ("grupo",          10),
    "Group Stage - 3":             ("grupo",          10),
    "Group Stage - 4":             ("grupo",          10),
    "Group Stage - 5":             ("grupo",          10),
    "Group Stage - 6":             ("grupo",          10),
    "Group Stage - 7":             ("grupo",          10),
    "Group Stage - 8":             ("grupo",          10),
    "Group Stage - 9":             ("grupo",          10),
    "League Stage":                ("grupo",          10),
    # Rondas eliminatorias  (orden 15-50)
    "1st Round":                   ("ronda32",        15),
    "Round of 32":                 ("ronda32",        15),
    "Round of 16":                 ("ronda16",        20),
    "Last 16":                     ("ronda16",        20),
    "Quarter-finals":              ("cuartos",        30),
    "Quarter Finals":              ("cuartos",        30),
    "Semi-finals":                 ("semis",          40),
    "Semi Finals":                 ("semis",          40),
    "3rd Place Final":             ("tercer_puesto",  45),
    "Final":                       ("final",          50),
}

FASE_NOMBRE_ES: dict[str, str] = {
    "grupo":           "",          # se rellena con el nombre del grupo (A, B, C…)
    "ronda32":         "Ronda de 32",
    "ronda16":         "Octavos de Final",
    "cuartos":         "Cuartos de Final",
    "semis":           "Semifinales",
    "tercer_puesto":   "Tercer Puesto",
    "final":           "Final",
    "clasificatoria":  "Clasificatoria",
    "playoff_prev":    "Playoff",
}

ESTADO_MAP: dict[str, str] = {
    "NS":  "programado",
    "1H":  "en_juego",
    "HT":  "en_juego",
    "2H":  "en_juego",
    "ET":  "en_juego",
    "BT":  "en_juego",
    "P":   "en_juego",
    "SUSP":"suspendido",
    "INT": "en_juego",
    "PST": "aplazado",
    "CANC":"suspendido",
    "ABD": "suspendido",
    "AWD": "finalizado",
    "WO":  "finalizado",
    "FT":  "finalizado",
    "AET": "finalizado",
    "PEN": "finalizado",
}


# ── Cliente HTTP ───────────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "x-apisports-key": API_KEY,
    }


async def _get(path: str, params: dict | None = None) -> dict:
    """GET a la API-Football. Levanta ValueError si falta la API key."""
    if not API_KEY:
        raise ValueError(
            "APIFOOTBALL_KEY no configurada en .env. "
            "Obtené tu clave gratuita en https://dashboard.api-football.com/register"
        )
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_BASE}{path}", headers=_headers(), params=params or {})
        r.raise_for_status()
        return r.json()


# ── Helpers de base de datos ───────────────────────────────────────────────────

async def _upsert_equipo(conn, team: dict) -> int:
    """Inserta o actualiza un equipo y devuelve su id interno."""
    api_id   = team.get("id")
    nombre   = team.get("name", "")
    logo     = team.get("logo", "")
    pais     = team.get("country", "")

    r = await conn.execute(
        text("""
            INSERT INTO equipo (api_team_id, nombre, nombre_es, pais, tipo, logo_url)
            VALUES (:api_id, :nombre, :nombre, :pais, :tipo, :logo)
            ON CONFLICT (api_team_id) DO UPDATE
                SET nombre   = EXCLUDED.nombre,
                    logo_url = EXCLUDED.logo_url
            RETURNING id
        """),
        {"api_id": api_id, "nombre": nombre, "pais": pais,
         "tipo": "seleccion", "logo": logo}
    )
    return r.scalar_one()


def _normalizar_grupo(raw: str) -> str:
    """
    Convierte el nombre de grupo de la API al formato español normalizado.
    Ejemplos:
      "Group Stage: Group A"  → "Grupo A"
      "Group A"               → "Grupo A"
      "FIFA World Cup - Group A" → "Grupo A"
    """
    import re
    # Buscar letra/número de grupo al final: "...Group A", "...Group 1"
    m = re.search(r'\bGroup\s+([A-Z0-9]+)\s*$', raw, re.IGNORECASE)
    if m:
        return f"Grupo {m.group(1).upper()}"
    # Si no tiene "Group" pero tiene letra sola, usar raw simplificado
    return raw.strip()


async def _get_or_create_fase(conn, torneo_id: int, nombre: str, tipo: str, orden: int) -> int:
    r = await conn.execute(
        text("""
            INSERT INTO fase (torneo_id, nombre, tipo, orden)
            VALUES (:tid, :nombre, :tipo, :orden)
            ON CONFLICT (torneo_id, nombre) DO UPDATE SET tipo=EXCLUDED.tipo
            RETURNING id
        """),
        {"tid": torneo_id, "nombre": nombre, "tipo": tipo, "orden": orden}
    )
    return r.scalar_one()


# ── Función principal: cargar torneo desde la API ──────────────────────────────

async def sincronizar_competiciones(engine: AsyncEngine) -> dict:
    """
    Consulta API-Football por todas las ligas soportadas, actualiza la tabla
    `competicion` y crea/actualiza registros en `torneo` para las temporadas activas.
    Devuelve un resumen de lo que se insertó/actualizó.
    """
    counts = {"competiciones": 0, "torneos": 0}

    for league_id, (nombre, tipo, formato, emoji) in LIGAS_SOPORTADAS.items():
        try:
            data = await _get("/leagues", {"id": league_id, "current": "true"})
        except Exception as e:
            log.warning("Error consultando liga %s: %s", league_id, e)
            continue

        resp = data.get("response", [])
        if not resp:
            continue

        league_info = resp[0]["league"]
        seasons     = resp[0].get("seasons", [])

        # Nombre oficial de la API (fallback al nuestro en español)
        nombre_api = nombre  # preferimos el nombre en español

        async with engine.begin() as conn:
            # Upsert competicion
            await conn.execute(
                text("""
                    INSERT INTO competicion (nombre, nombre_corto, tipo, formato_playoff, api_league_id, emoji)
                    VALUES (:nombre, :corto, :tipo, :fmt, :lid, :emoji)
                    ON CONFLICT (api_league_id) DO UPDATE SET
                        nombre       = EXCLUDED.nombre,
                        nombre_corto = EXCLUDED.nombre_corto,
                        emoji        = EXCLUDED.emoji,
                        es_activo    = TRUE
                """),
                {"nombre": nombre, "corto": nombre.split()[-1], "tipo": tipo,
                 "fmt": formato, "lid": league_id, "emoji": emoji}
            )
            counts["competiciones"] += 1

            # Upsert torneos para cada temporada activa
            for season in seasons:
                if not season.get("current"):
                    continue
                anio       = season["year"]
                api_season = season["year"]
                estado     = "en_curso"
                nombre_torneo = f"{nombre} {anio}"

                await conn.execute(
                    text("""
                        INSERT INTO torneo (competicion_id, anio, nombre, api_season, estado)
                        SELECT id, :anio, :nombre, :api_season, :estado
                        FROM competicion WHERE api_league_id = :lid
                        ON CONFLICT (competicion_id, anio) DO UPDATE SET
                            api_season = EXCLUDED.api_season,
                            estado     = EXCLUDED.estado,
                            nombre     = EXCLUDED.nombre
                    """),
                    {"anio": anio, "nombre": nombre_torneo,
                     "api_season": api_season, "estado": estado, "lid": league_id}
                )
                counts["torneos"] += 1

    return counts


async def cargar_torneo(engine: AsyncEngine, torneo_id: int) -> dict:
    """
    Lee la BD para obtener league_id + season, luego:
      1. Descarga fixtures desde API-Football
      2. Inserta/actualiza equipos, fases, participaciones, partidos
    Devuelve un resumen {torneos, equipos, fases, partidos}.
    """
    async with engine.begin() as conn:
        row = await conn.execute(
            text("""
                SELECT t.id, t.anio, t.api_season, c.api_league_id, c.tipo, c.formato_playoff
                FROM torneo t
                JOIN competicion c ON c.id = t.competicion_id
                WHERE t.id = :tid
            """),
            {"tid": torneo_id}
        )
        torneo = row.mappings().one_or_none()
        if not torneo:
            raise ValueError(f"Torneo {torneo_id} no encontrado")

    league_id = torneo["api_league_id"]
    season    = torneo["api_season"] or torneo["anio"]
    tipo_comp = torneo["tipo"]
    fmt       = torneo["formato_playoff"]

    log.info("Cargando torneo %s — league=%s season=%s", torneo_id, league_id, season)

    # ── Descargar fixtures (paginados de a 100) ────────────────────────────────
    data = await _get("/fixtures", {"league": league_id, "season": season})
    fixtures = data.get("response", [])
    log.info("API devolvió %d partidos", len(fixtures))

    # ── Descargar standings (para grupos) ─────────────────────────────────────
    standings_data = await _get("/standings", {"league": league_id, "season": season})
    standings_resp = standings_data.get("response", [])

    # Construir dict {equipo_api_id: {pj,pg,pe,pp,gf,gc,pts,pos,clasifica,grupo_nombre,team_info}}
    standings_map: dict[int, dict] = {}
    for league_block in standings_resp:
        for group_list in league_block.get("league", {}).get("standings", []):
            for entry in group_list:
                tid = entry["team"]["id"]
                # Normalizar nombre del grupo
                raw_grupo = entry.get("group", "")
                standings_map[tid] = {
                    "pj": entry["all"]["played"],
                    "pg": entry["all"]["win"],
                    "pe": entry["all"]["draw"],
                    "pp": entry["all"]["lose"],
                    "gf": entry["all"]["goals"]["for"],
                    "gc": entry["all"]["goals"]["against"],
                    "pts": entry["points"],
                    "pos": entry["rank"],
                    "grupo": raw_grupo,
                    "clasifica": entry.get("promotion", {}).get("status") in
                                  ("Promotion", "Promotion - Play-offs"),
                    # Guardar info del equipo para pre-cargarlo
                    "_team": entry["team"],
                }

    log.info("standings_map: %d equipos, grupos: %s",
             len(standings_map),
             sorted({v.get("grupo","") for v in standings_map.values()}))
    counts = {"equipos": 0, "fases": 0, "partidos": 0, "participaciones": 0}

    async with engine.begin() as conn:
        # Cache de fases ya creadas {nombre: id}
        fases_cache: dict[str, int] = {}
        # Cache de equipos {api_team_id: internal_id}
        equipos_cache: dict[int, int] = {}

        # ── PRE-CARGAR todos los equipos del standings ────────────────────────
        # Esto garantiza que los 4 equipos de cada grupo estén en cache
        # incluso si alguno no tiene fixtures cargados todavía
        tipo_eq_global = "seleccion" if tipo_comp == "paises" else "club"
        for api_tid, st_data in standings_map.items():
            team_info = st_data.get("_team", {})
            r_eq = await conn.execute(
                text("""
                    INSERT INTO equipo (api_team_id, nombre, nombre_es, pais, tipo, logo_url)
                    VALUES (:api_id, :nombre, :nombre, :pais, :tipo, :logo)
                    ON CONFLICT (api_team_id) DO UPDATE
                        SET nombre=EXCLUDED.nombre, logo_url=EXCLUDED.logo_url
                    RETURNING id
                """),
                {
                    "api_id": api_tid,
                    "nombre": team_info.get("name", str(api_tid)),
                    "pais": team_info.get("country", ""),
                    "tipo": tipo_eq_global,
                    "logo": team_info.get("logo", ""),
                }
            )
            eq_id = r_eq.scalar_one()
            equipos_cache[api_tid] = eq_id
            # (torneo_equipo: tabla eliminada del esquema — equipos_cache cubre
            #  la relación api_team_id → equipo_id en memoria.)

        # ── PRE-CREAR fases de grupos desde standings ─────────────────────────
        # Así el grupo_nombre queda normalizado igual para todos los equipos
        # También construir mapa api_team_id → grupo_nombre para asignación rápida
        equipo_grupo_map: dict[int, str] = {}   # api_team_id → "Grupo A"
        for api_tid, st_data in standings_map.items():
            raw_grupo = st_data.get("grupo", "")
            if not raw_grupo:
                continue
            nombre_fase_grupo = _normalizar_grupo(raw_grupo)
            if nombre_fase_grupo not in fases_cache:
                fid = await _get_or_create_fase(conn, torneo_id, nombre_fase_grupo, "grupo", 10)
                fases_cache[nombre_fase_grupo] = fid
                counts["fases"] += 1
            equipo_grupo_map[api_tid] = nombre_fase_grupo

        # Runtime: se completa durante el loop cuando vemos equipos que no están
        # en standings_map pero sus compañeros de partido sí lo están.
        equipo_grupo_runtime: dict[int, str] = dict(equipo_grupo_map)

        for fx in fixtures:
            fix     = fx["fixture"]
            league  = fx["league"]
            teams   = fx["teams"]
            goals   = fx["goals"]
            score   = fx["score"]

            api_fix_id = fix["id"]
            round_str  = league.get("round", "")        # e.g. "Group Stage - 1", "Quarter-finals"
            fecha_raw  = fix.get("date")
            fecha = None
            if fecha_raw:
                from datetime import datetime, timezone
                try:
                    fecha = datetime.fromisoformat(fecha_raw)
                except ValueError:
                    fecha = None
            estado_raw = fix["status"]["short"]
            estado     = ESTADO_MAP.get(estado_raw, "programado")
            sede       = fix.get("venue", {}).get("name", "")
            ciudad     = fix.get("venue", {}).get("city", "")

            # Determinar tipo/orden de fase
            tipo_fase, orden_fase = FASE_MAP.get(round_str, ("otro", 99))

            # Nombre legible de la fase en español
            if tipo_fase == "grupo":
                # round_str es algo como "Group Stage - 1" o "Group A"
                # Intentar extraer letra del grupo del nombre del grupo en standings
                nombre_fase = round_str  # se mejora más abajo
            else:
                nombre_fase = FASE_NOMBRE_ES.get(tipo_fase, round_str)

            # Equipos
            for side in ("home", "away"):
                t = teams[side]
                api_tid = t["id"]
                if api_tid not in equipos_cache:
                    tipo_eq = "seleccion" if tipo_comp == "paises" else "club"
                    r2 = await conn.execute(
                        text("""
                            INSERT INTO equipo (api_team_id, nombre, nombre_es, pais, tipo, logo_url)
                            VALUES (:api_id, :nombre, :nombre, :pais, :tipo, :logo)
                            ON CONFLICT (api_team_id) DO UPDATE
                                SET nombre=EXCLUDED.nombre, logo_url=EXCLUDED.logo_url
                            RETURNING id
                        """),
                        {"api_id": api_tid, "nombre": t["name"], "pais": t.get("country",""),
                         "tipo": tipo_eq, "logo": t.get("logo","")}
                    )
                    eq_id = r2.scalar_one()
                    equipos_cache[api_tid] = eq_id
                    counts["equipos"] += 1
                    # (torneo_equipo: tabla eliminada — equipos_cache cubre la relación)

            local_id     = equipos_cache[teams["home"]["id"]]
            visitante_id = equipos_cache[teams["away"]["id"]]

            # Fase — para grupos usar el nombre normalizado desde standings
            home_api = teams["home"]["id"]
            away_api = teams["away"]["id"]
            if tipo_fase == "grupo":
                # Intentar con el mapa pre-construido (standings + runtime)
                nombre_fase = (
                    equipo_grupo_runtime.get(home_api) or
                    equipo_grupo_runtime.get(away_api)
                )
                if not nombre_fase:
                    # Último recurso: intentar extraer del round_str
                    raw_grupo = standings_map.get(home_api, {}).get("grupo") or \
                                standings_map.get(away_api, {}).get("grupo") or \
                                round_str
                    nombre_fase = _normalizar_grupo(raw_grupo)

                # Registrar ambos equipos en runtime — solo sobreescribir con "Grupo X" real
                # (no sobreescribir una asignación correcta con un fallback genérico)
                if nombre_fase and nombre_fase.startswith("Grupo "):
                    equipo_grupo_runtime[home_api] = nombre_fase
                    equipo_grupo_runtime[away_api] = nombre_fase
                elif nombre_fase and home_api not in equipo_grupo_runtime:
                    equipo_grupo_runtime[home_api] = nombre_fase
                if nombre_fase and not nombre_fase.startswith("Grupo ") and away_api not in equipo_grupo_runtime:
                    equipo_grupo_runtime[away_api] = nombre_fase

            if nombre_fase not in fases_cache:
                fid = await _get_or_create_fase(conn, torneo_id, nombre_fase, tipo_fase, orden_fase)
                fases_cache[nombre_fase] = fid
                counts["fases"] += 1

            fase_id = fases_cache[nombre_fase]

            # Jornada (número de ronda)
            import re
            jornada = None
            m = re.search(r"(\d+)", round_str)
            if m:
                jornada = int(m.group(1))

            # Resultado
            g_local = goals.get("home")
            g_visit = goals.get("away")

            # Prórroga
            et = score.get("extratime", {}) or {}
            g_local_et = et.get("home")
            g_visit_et = et.get("away")

            # Penales
            pen = score.get("penalty", {}) or {}
            p_local = pen.get("home")
            p_visit = pen.get("away")

            # Leg (ida/vuelta para clubes)
            if fmt == "ida_vuelta" and tipo_fase != "grupo":
                if "1st" in round_str or "Leg 1" in round_str or "First" in round_str:
                    leg = "ida"
                elif "2nd" in round_str or "Leg 2" in round_str or "Second" in round_str:
                    leg = "vuelta"
                else:
                    leg = "unico"
            else:
                leg = "unico"

            await conn.execute(
                text("""
                    INSERT INTO partido (
                        torneo_id, fase_id, jornada,
                        equipo_local_id, equipo_visitante_id,
                        fecha, sede, ciudad,
                        goles_local, goles_visitante,
                        goles_local_prorroga, goles_visitante_prorroga,
                        penales_local, penales_visitante,
                        estado, leg, api_fixture_id
                    ) VALUES (
                        :tid, :fid, :jornada,
                        :local_id, :visit_id,
                        :fecha, :sede, :ciudad,
                        :gl, :gv,
                        :gl_et, :gv_et,
                        :pl, :pv,
                        :estado, :leg, :api_fix
                    )
                    ON CONFLICT (api_fixture_id) DO UPDATE SET
                        goles_local             = EXCLUDED.goles_local,
                        goles_visitante         = EXCLUDED.goles_visitante,
                        goles_local_prorroga    = EXCLUDED.goles_local_prorroga,
                        goles_visitante_prorroga= EXCLUDED.goles_visitante_prorroga,
                        penales_local           = EXCLUDED.penales_local,
                        penales_visitante       = EXCLUDED.penales_visitante,
                        estado                  = EXCLUDED.estado
                """),
                {
                    "tid": torneo_id, "fid": fase_id, "jornada": jornada,
                    "local_id": local_id, "visit_id": visitante_id,
                    "fecha": fecha, "sede": sede, "ciudad": ciudad,
                    "gl": g_local, "gv": g_visit,
                    "gl_et": g_local_et, "gv_et": g_visit_et,
                    "pl": p_local, "pv": p_visit,
                    "estado": estado, "leg": leg, "api_fix": api_fix_id
                }
            )
            counts["partidos"] += 1

        # ── Standings / Participaciones ────────────────────────────────────────
        for api_tid, st in standings_map.items():
            if api_tid not in equipos_cache:
                continue
            equipo_id   = equipos_cache[api_tid]
            raw_grupo   = st.get("grupo", "")
            nombre_fase = _normalizar_grupo(raw_grupo) if raw_grupo else ""

            # Si el grupo está vacío, intentar inferirlo desde los partidos ya cargados
            if not nombre_fase:
                r_infer = await conn.execute(
                    text("""
                        SELECT f.nombre FROM partido p
                        JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
                        WHERE p.torneo_id = :tid
                          AND (p.equipo_local_id = :eid OR p.equipo_visitante_id = :eid)
                        LIMIT 1
                    """),
                    {"tid": torneo_id, "eid": equipo_id}
                )
                infer_row = r_infer.one_or_none()
                if infer_row:
                    nombre_fase = infer_row[0]
                else:
                    log.warning("Equipo api_id=%s sin grupo en standings y sin partidos de grupo", api_tid)
                    continue

            if nombre_fase not in fases_cache:
                fid = await _get_or_create_fase(conn, torneo_id, nombre_fase, "grupo", 10)
                fases_cache[nombre_fase] = fid

            fase_id = fases_cache[nombre_fase]
            await conn.execute(
                text("""
                    INSERT INTO participacion
                        (fase_id, equipo_id, posicion, pj, pg, pe, pp, gf, gc, pts, clasifica)
                    VALUES
                        (:fid, :eid, :pos, :pj, :pg, :pe, :pp, :gf, :gc, :pts, :clasifica)
                    ON CONFLICT (fase_id, equipo_id) DO UPDATE SET
                        posicion = EXCLUDED.posicion,
                        pj=EXCLUDED.pj, pg=EXCLUDED.pg, pe=EXCLUDED.pe, pp=EXCLUDED.pp,
                        gf=EXCLUDED.gf, gc=EXCLUDED.gc, pts=EXCLUDED.pts,
                        clasifica=EXCLUDED.clasifica
                """),
                {
                    "fid": fase_id, "eid": equipo_id,
                    "pos": st["pos"], "pj": st["pj"], "pg": st["pg"],
                    "pe": st["pe"], "pp": st["pp"], "gf": st["gf"],
                    "gc": st["gc"], "pts": st["pts"],
                    "clasifica": st.get("clasifica", False)
                }
            )
            counts["participaciones"] += 1

        # ── Completar participaciones faltantes desde partidos de grupo ────────
        # Garantiza que todo equipo con partidos en un grupo aparezca en standings,
        # aunque no haya venido en el response de la API de standings.
        r_miss = await conn.execute(
            text("""
                SELECT DISTINCT f.id AS fase_id, p.equipo_local_id AS equipo_id
                FROM partido p JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
                WHERE p.torneo_id = :tid
                UNION
                SELECT DISTINCT f.id AS fase_id, p.equipo_visitante_id AS equipo_id
                FROM partido p JOIN fase f ON f.id = p.fase_id AND f.tipo = 'grupo'
                WHERE p.torneo_id = :tid
            """),
            {"tid": torneo_id}
        )
        for miss in r_miss.mappings():
            await conn.execute(
                text("""
                    INSERT INTO participacion
                        (fase_id, equipo_id, posicion, pj, pg, pe, pp, gf, gc, pts, clasifica)
                    VALUES (:fid, :eid, 0, 0, 0, 0, 0, 0, 0, 0, false)
                    ON CONFLICT (fase_id, equipo_id) DO NOTHING
                """),
                {"fid": miss["fase_id"], "eid": miss["equipo_id"]}
            )
            counts["participaciones"] += 1

        # ── Inferir posiciones faltantes en standings ─────────────────────────
        # Preserva los # ya asignados; solo rellena los que llegaron como NULL/0
        await _inferir_posiciones_torneo(conn, torneo_id)

        # ── Reparar partidos en fases genéricas (Group Stage - N) ───────────────
        # Usamos equipos_cache invertido (db_eq_id → api_team_id) para no depender
        # de que torneo_equipo.api_team_id esté correctamente poblado.
        inv_eq = {v: k for k, v in equipos_cache.items()}

        r_bad = await conn.execute(
            text("""
                SELECT p.id, p.equipo_local_id, p.equipo_visitante_id
                FROM partido p
                JOIN fase f ON f.id = p.fase_id
                WHERE p.torneo_id = :tid
                  AND f.tipo = 'grupo'
                  AND f.nombre NOT LIKE 'Grupo %'
            """),
            {"tid": torneo_id}
        )
        bad_rows = [dict(r) for r in r_bad.mappings()]
        for row in bad_rows:
            local_api = inv_eq.get(row["equipo_local_id"])
            visit_api = inv_eq.get(row["equipo_visitante_id"])
            grupo_correcto = (
                (local_api and equipo_grupo_runtime.get(local_api)) or
                (visit_api and equipo_grupo_runtime.get(visit_api))
            )
            if grupo_correcto and grupo_correcto.startswith("Grupo ") and grupo_correcto in fases_cache:
                await conn.execute(
                    text("UPDATE partido SET fase_id=:fid WHERE id=:pid"),
                    {"fid": fases_cache[grupo_correcto], "pid": row["id"]}
                )
                counts["reasignados"] = counts.get("reasignados", 0) + 1

        # Marcar torneo como datos cargados
        await conn.execute(
            text("UPDATE torneo SET datos_cargados=TRUE WHERE id=:tid"),
            {"tid": torneo_id}
        )

        # ── Recalcular standings desde resultados reales ──────────────────────
        # Garantiza que participacion refleje SOLO los partidos finalizados
        # en ESTE torneo, no datos de qualifiers o temporadas anteriores de la API.
        await _recalc_grupo_standings(conn, torneo_id)

    return counts


async def _recalc_grupo_standings(conn, torneo_id: int) -> None:
    """
    Recalcula PJ/PG/PE/PP/GF/GC/Pts en participacion a partir de los partidos
    finalizados del torneo. Si no hay partidos jugados, todo queda en cero.
    Llama a _inferir_posiciones_torneo al final para ordenar posiciones.
    """
    await conn.execute(
        text("""
            UPDATE participacion p
            SET pj=s.pj, pg=s.pg, pe=s.pe, pp=s.pp,
                gf=s.gf, gc=s.gc,
                pts = s.pg * 3 + s.pe
            FROM (
                SELECT fase_id, equipo_id,
                    SUM(pj)::int AS pj,
                    SUM(pg)::int AS pg,
                    SUM(pe)::int AS pe,
                    SUM(pp)::int AS pp,
                    SUM(gf)::int AS gf,
                    SUM(gc)::int AS gc
                FROM (
                    -- Como local
                    SELECT f.id AS fase_id, pa.equipo_local_id AS equipo_id,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado') AS pj,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_local > pa.goles_visitante) AS pg,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_local = pa.goles_visitante) AS pe,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_local < pa.goles_visitante) AS pp,
                        COALESCE(SUM(pa.goles_local)
                            FILTER (WHERE pa.estado='finalizado'), 0) AS gf,
                        COALESCE(SUM(pa.goles_visitante)
                            FILTER (WHERE pa.estado='finalizado'), 0) AS gc
                    FROM partido pa
                    JOIN fase f ON f.id = pa.fase_id AND f.tipo = 'grupo'
                    WHERE pa.torneo_id = :tid
                    GROUP BY f.id, pa.equipo_local_id
                    UNION ALL
                    -- Como visitante
                    SELECT f.id AS fase_id, pa.equipo_visitante_id AS equipo_id,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado') AS pj,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_visitante > pa.goles_local) AS pg,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_local = pa.goles_visitante) AS pe,
                        COUNT(*) FILTER (WHERE pa.estado='finalizado'
                            AND pa.goles_visitante < pa.goles_local) AS pp,
                        COALESCE(SUM(pa.goles_visitante)
                            FILTER (WHERE pa.estado='finalizado'), 0) AS gf,
                        COALESCE(SUM(pa.goles_local)
                            FILTER (WHERE pa.estado='finalizado'), 0) AS gc
                    FROM partido pa
                    JOIN fase f ON f.id = pa.fase_id AND f.tipo = 'grupo'
                    WHERE pa.torneo_id = :tid
                    GROUP BY f.id, pa.equipo_visitante_id
                ) sub
                GROUP BY fase_id, equipo_id
            ) s
            WHERE p.fase_id = s.fase_id AND p.equipo_id = s.equipo_id
        """),
        {"tid": torneo_id}
    )
    # Equipos sin ningún partido aún → cero todo
    await conn.execute(
        text("""
            UPDATE participacion p
            SET pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0
            FROM fase f
            WHERE p.fase_id = f.id
              AND f.torneo_id = :tid
              AND f.tipo = 'grupo'
              AND NOT EXISTS (
                  SELECT 1 FROM partido pa
                  WHERE pa.fase_id = f.id
                    AND pa.estado = 'finalizado'
                    AND (pa.equipo_local_id = p.equipo_id
                         OR pa.equipo_visitante_id = p.equipo_id)
              )
        """),
        {"tid": torneo_id}
    )
    await _inferir_posiciones_torneo(conn, torneo_id)


async def _inferir_posiciones_torneo(conn, torneo_id: int) -> int:
    """
    Para cada fase de grupos del torneo, detecta qué posiciones (1..N) ya están
    asignadas y rellena los huecos (NULL o 0) con los números faltantes,
    ordenando por pts DESC, diferencia de goles DESC, goles a favor DESC.
    Devuelve el número de filas actualizadas.
    """
    r = await conn.execute(
        text("SELECT id FROM fase WHERE torneo_id=:tid AND tipo='grupo'"),
        {"tid": torneo_id}
    )
    fase_ids = [row[0] for row in r]
    updated = 0

    for fid in fase_ids:
        r2 = await conn.execute(
            text("""
                SELECT id, posicion, pts, gf, gc
                FROM participacion
                WHERE fase_id = :fid
                ORDER BY pts DESC, (gf - gc) DESC, gf DESC
            """),
            {"fid": fid}
        )
        rows = list(r2.mappings())
        total = len(rows)
        usados = {row["posicion"] for row in rows if row["posicion"]}
        faltantes = [i for i in range(1, total + 1) if i not in usados]
        fi = 0
        for row in rows:
            if not row["posicion"] and fi < len(faltantes):
                await conn.execute(
                    text("UPDATE participacion SET posicion=:pos WHERE id=:id"),
                    {"pos": faltantes[fi], "id": row["id"]}
                )
                fi += 1
                updated += 1

    log.info("Posiciones inferidas: %d fila(s) actualizadas para torneo %s", updated, torneo_id)
    return updated


async def cargar_estadisticas_partido(engine: AsyncEngine, partido_id: int) -> dict:
    """
    Carga estadísticas y eventos de un partido específico desde la API.
    Guarda en partido_estadistica y partido_evento.
    """
    async with engine.begin() as conn:
        row = await conn.execute(
            text("SELECT api_fixture_id FROM partido WHERE id=:pid"),
            {"pid": partido_id}
        )
        r = row.one_or_none()
        if not r or not r[0]:
            raise ValueError(f"Partido {partido_id} no tiene api_fixture_id")
        api_fix_id = r[0]

    # Estadísticas
    stats_data = await _get("/fixtures/statistics", {"fixture": api_fix_id})
    # Eventos
    events_data = await _get("/fixtures/events", {"fixture": api_fix_id})

    async with engine.begin() as conn:
        # ── Upsert estadísticas ────────────────────────────────────────────────
        for team_stats in stats_data.get("response", []):
            api_team_id = team_stats["team"]["id"]
            r = await conn.execute(
                text("SELECT id FROM equipo WHERE api_team_id=:atid"),
                {"atid": api_team_id}
            )
            eq_row = r.one_or_none()
            if not eq_row:
                continue
            equipo_id = eq_row[0]

            # Mapear estadísticas a columnas estructuradas
            raw: dict = {s["type"]: s["value"] for s in team_stats.get("statistics", [])}

            def _int(key: str):
                v = raw.get(key)
                if v is None:
                    return None
                try:
                    return int(str(v).replace("%", ""))
                except (ValueError, TypeError):
                    return None

            def _pct(key: str):
                v = raw.get(key)
                if v is None:
                    return None
                try:
                    return float(str(v).replace("%", ""))
                except (ValueError, TypeError):
                    return None

            await conn.execute(
                text("""
                    INSERT INTO partido_estadistica (
                        partido_id, equipo_id,
                        tiros_total, tiros_al_arco, posesion,
                        pases_total, pases_precision,
                        faltas, tarjetas_amarillas, tarjetas_rojas,
                        fueras_de_juego, corners, datos_extra
                    ) VALUES (
                        :pid, :eid,
                        :tt, :ta, :pos,
                        :pt, :pp,
                        :f, :ya, :yr,
                        :ofs, :cor, :extra
                    )
                    ON CONFLICT (partido_id, equipo_id) DO UPDATE SET
                        tiros_total=EXCLUDED.tiros_total,
                        tiros_al_arco=EXCLUDED.tiros_al_arco,
                        posesion=EXCLUDED.posesion,
                        pases_total=EXCLUDED.pases_total,
                        pases_precision=EXCLUDED.pases_precision,
                        faltas=EXCLUDED.faltas,
                        tarjetas_amarillas=EXCLUDED.tarjetas_amarillas,
                        tarjetas_rojas=EXCLUDED.tarjetas_rojas,
                        fueras_de_juego=EXCLUDED.fueras_de_juego,
                        corners=EXCLUDED.corners,
                        datos_extra=EXCLUDED.datos_extra
                """),
                {
                    "pid": partido_id, "eid": equipo_id,
                    "tt":  _int("Total Shots"),
                    "ta":  _int("Shots on Goal"),
                    "pos": _pct("Ball Possession"),
                    "pt":  _int("Total passes"),
                    "pp":  _pct("Passes %"),
                    "f":   _int("Fouls"),
                    "ya":  _int("Yellow Cards"),
                    "yr":  _int("Red Cards"),
                    "ofs": _int("Offsides"),
                    "cor": _int("Corner Kicks"),
                    "extra": __import__("json").dumps(raw),
                }
            )

        # ── Borrar eventos previos e insertar nuevos ───────────────────────────
        await conn.execute(
            text("DELETE FROM partido_evento WHERE partido_id=:pid"),
            {"pid": partido_id}
        )

        TIPO_MAP = {
            "Goal":          "gol",
            "Normal Goal":   "gol",
            "Penalty":       "penal",
            "Own Goal":      "autogol",
            "Missed Penalty":"penal_fallado",
            "Yellow Card":   "amarilla",
            "Red Card":      "roja",
            "Yellow Red Card":"roja",
            "subst":         "sustitucion",
            "Substitution 1":"sustitucion",
            "Substitution 2":"sustitucion",
            "Substitution 3":"sustitucion",
        }

        for ev in events_data.get("response", []):
            api_team_id = ev["team"]["id"]
            r = await conn.execute(
                text("SELECT id FROM equipo WHERE api_team_id=:atid"),
                {"atid": api_team_id}
            )
            eq_row = r.one_or_none()
            equipo_id = eq_row[0] if eq_row else None

            tipo_raw = ev.get("type", "")
            detail   = ev.get("detail", "")
            tipo     = TIPO_MAP.get(detail) or TIPO_MAP.get(tipo_raw, tipo_raw.lower())

            player   = ev.get("player", {}) or {}
            assist   = ev.get("assist", {}) or {}
            time_obj = ev.get("time", {}) or {}

            await conn.execute(
                text("""
                    INSERT INTO partido_evento (
                        partido_id, equipo_id, tipo, minuto, minuto_extra,
                        jugador_nombre, jugador_api_id, asistencia_nombre, detalle
                    ) VALUES (
                        :pid, :eid, :tipo, :min, :min_extra,
                        :jugador, :jid, :asistencia, :detalle
                    )
                """),
                {
                    "pid": partido_id, "eid": equipo_id,
                    "tipo": tipo,
                    "min": time_obj.get("elapsed"),
                    "min_extra": time_obj.get("extra"),
                    "jugador": player.get("name"),
                    "jid": player.get("id"),
                    "asistencia": assist.get("name"),
                    "detalle": detail,
                }
            )

    # ── Derivar penales_partido desde eventos (penal + penal_fallado) ──────
    # Solo contamos eventos de tiempo reglamentario/prórroga, no tanda.
    # En API-Football los eventos de tanda no tienen minuto estándar o son
    # registrados con type="Penalty" detail="Penalty" pero sin minutos reales;
    # filtramos: penales durante el partido = eventos tipo penal|penal_fallado
    # con minuto <= 120 (excluye shootout que reportan minuto=None o muy alto).
    try:
        pen_res = await conn.execute(
            text("""
                SELECT COUNT(*) FROM partido_evento
                WHERE partido_id = :pid
                  AND tipo IN ('penal', 'penal_fallado')
                  AND (minuto IS NULL OR minuto <= 120)
            """),
            {"pid": partido_id}
        )
        pen_count = pen_res.scalar_one()
        await conn.execute(
            text("UPDATE partido SET penales_partido = :pc WHERE id = :pid"),
            {"pc": int(pen_count), "pid": partido_id}
        )
    except Exception:
        pass  # columna puede no existir aún en entornos sin migración

    return {"ok": True, "api_fixture_id": api_fix_id}
