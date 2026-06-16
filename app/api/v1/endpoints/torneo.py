"""
Endpoints de Torneos de Fútbol
────────────────────────────────
GET  /torneo/competiciones              → catálogo de competiciones
GET  /torneo/torneos                    → ediciones disponibles (con filtro)
POST /torneo/torneos                    → crear edición
POST /torneo/torneos/{id}/cargar        → cargar datos desde API-Football
GET  /torneo/torneos/{id}/fixture       → fixture completo (fases + partidos)
GET  /torneo/torneos/{id}/grupos        → fase de grupos con standings
GET  /torneo/partidos/{id}/estadisticas → estadísticas + eventos de un partido
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import CurrentUser, CurrentAdmin, BECBUCSession as DBSession
from app.db.session import _becbuc_engine as engine
from app.services import torneo_service

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class TorneoCreate(BaseModel):
    competicion_id: int
    anio: int
    sede: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sincronizar", summary="Sincronizar competiciones y temporadas activas desde API")
async def sincronizar(_: CurrentUser) -> dict:
    """Consulta API-Football y actualiza competicion + torneo con las temporadas activas."""
    try:
        counts = await torneo_service.sincronizar_competiciones(engine)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, **counts}


@router.get("/probar-api", summary="Probar la conexión con API-Football")
async def probar_api(_: CurrentAdmin) -> dict:
    """Verifica la conectividad y la API key consultando el endpoint /status de
    API-Football. Devuelve si la conexión es válida y la cuota de requests del día."""
    from app.services.torneo_service import API_KEY, _get

    if not API_KEY or API_KEY == "TU_API_KEY_AQUI":
        return {
            "ok": False,
            "configurada": False,
            "mensaje": "APIFOOTBALL_KEY no configurada en .env",
        }
    try:
        data = await _get("/status")
    except Exception as e:
        return {"ok": False, "configurada": True, "mensaje": f"Error de conexión: {e}"}

    resp = data.get("response", {}) or {}
    cuenta = resp.get("account", {}) or {}
    sub = resp.get("subscription", {}) or {}
    reqs = resp.get("requests", {}) or {}
    return {
        "ok": True,
        "configurada": True,
        "mensaje": "Conexión exitosa con API-Football",
        "cuenta": f"{cuenta.get('firstname','')} {cuenta.get('lastname','')}".strip() or None,
        "email": cuenta.get("email"),
        "plan": sub.get("plan"),
        "activo": sub.get("active"),
        "requests_hoy": reqs.get("current"),
        "requests_limite": reqs.get("limit_day"),
    }


@router.get("/competiciones", summary="Listar competiciones soportadas")
async def list_competiciones(db: DBSession) -> list[dict]:
    r = await db.execute(
        text("SELECT id, nombre, nombre_corto, tipo, formato_playoff, emoji FROM competicion WHERE es_activo ORDER BY id")
    )
    return [dict(row) for row in r.mappings()]


@router.get("/activas", summary="Torneos con temporada activa")
async def list_activas(db: DBSession) -> list[dict]:
    """Devuelve torneos en_curso o finalizados recientemente, con datos de competicion y resumen de fases."""
    r = await db.execute(
        text("""
            SELECT t.id, t.anio, t.nombre, t.estado, t.datos_cargados, t.api_season,
                   c.id AS competicion_id, c.nombre AS competicion,
                   c.nombre_corto, c.emoji, c.tipo, c.api_league_id, c.formato_playoff,
                   (SELECT COUNT(*) FROM fase f WHERE f.torneo_id = t.id AND f.tipo = 'grupo')::int AS num_grupos,
                   (SELECT COUNT(*) FROM partido p
                      JOIN fase f ON f.id = p.fase_id
                    WHERE f.torneo_id = t.id AND f.tipo = 'grupo')::int AS partidos_grupos,
                   (SELECT COUNT(*) FROM partido p
                      JOIN fase f ON f.id = p.fase_id
                    WHERE f.torneo_id = t.id AND f.tipo <> 'grupo')::int AS partidos_ko,
                   (SELECT COALESCE(json_agg(f2.nombre ORDER BY f2.orden), '[]'::json)
                      FROM fase f2 WHERE f2.torneo_id = t.id AND f2.tipo <> 'grupo') AS fases_ko
            FROM torneo t
            JOIN competicion c ON c.id = t.competicion_id
            WHERE c.es_activo = TRUE
            ORDER BY
                CASE t.estado WHEN 'en_curso' THEN 0 WHEN 'finalizado' THEN 1 ELSE 2 END,
                t.anio DESC, c.id
        """)
    )
    rows = []
    for row in r.mappings():
        d = dict(row)
        d["nombre"] = d["nombre"] or f"{d['competicion']} {d['anio']}"
        rows.append(d)
    return rows


@router.get("/torneos", summary="Listar ediciones de torneo")
async def list_torneos(
    db: DBSession,
    competicion_id: int | None = Query(None),
) -> list[dict]:
    q = """
        SELECT t.id, t.anio, t.nombre, t.estado, t.datos_cargados, t.sede,
               c.nombre AS competicion, c.nombre_corto, c.emoji, c.tipo,
               c.api_league_id, t.api_season
        FROM torneo t
        JOIN competicion c ON c.id = t.competicion_id
    """
    params: dict = {}
    if competicion_id:
        q += " WHERE t.competicion_id = :cid"
        params["cid"] = competicion_id
    q += " ORDER BY t.anio DESC, c.id"
    r = await db.execute(text(q), params)
    rows = []
    for row in r.mappings():
        d = dict(row)
        d["nombre"] = d["nombre"] or f"{d['competicion']} {d['anio']}"
        rows.append(d)
    return rows


@router.post("/torneos", summary="Crear edición de torneo")
async def create_torneo(body: TorneoCreate, _: CurrentUser, db: DBSession) -> dict:
    # Verificar que la competicion existe
    r = await db.execute(
        text("SELECT id, nombre, nombre_corto, api_league_id FROM competicion WHERE id=:cid"),
        {"cid": body.competicion_id}
    )
    comp = r.mappings().one_or_none()
    if not comp:
        raise HTTPException(404, "Competición no encontrada")

    nombre = f"{comp['nombre']} {body.anio}"
    try:
        r2 = await db.execute(
            text("""
                INSERT INTO torneo (competicion_id, anio, nombre, sede, api_season)
                VALUES (:cid, :anio, :nombre, :sede, :anio)
                RETURNING id
            """),
            {"cid": body.competicion_id, "anio": body.anio,
             "nombre": nombre, "sede": body.sede}
        )
        torneo_id = r2.scalar_one()
        await db.commit()
    except Exception as e:
        await db.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(409, f"Ya existe el torneo {nombre}")
        raise HTTPException(400, str(e))

    return {"id": torneo_id, "nombre": nombre}


@router.post("/torneos/{torneo_id}/inferir-posiciones", summary="Inferir posiciones faltantes en standings")
async def inferir_posiciones(torneo_id: int, _: CurrentUser) -> dict:
    """Detecta huecos en posicion (1..N) de cada grupo y los rellena sin tocar los ya asignados."""
    try:
        from app.services.torneo_service import _inferir_posiciones_torneo
        async with engine.begin() as conn:
            updated = await _inferir_posiciones_torneo(conn, torneo_id)
    except Exception as e:
        raise HTTPException(500, str(e))
    return {"ok": True, "torneo_id": torneo_id, "actualizadas": updated}


@router.post("/torneos/{torneo_id}/cargar", summary="Cargar datos desde API-Football")
async def cargar_datos(torneo_id: int, _: CurrentUser, db: DBSession) -> dict:
    try:
        counts = await torneo_service.cargar_torneo(engine, torneo_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

    # Avanzar bracket secuencialmente desde los resultados cargados
    try:
        from app.api.v1.endpoints.apostador_bets import _avanzar_bracket
        from app.services import ko_scoring
        maps = await ko_scoring.build_num_maps(db, torneo_id)
        await _avanzar_bracket(db, torneo_id, maps)
        await db.commit()
        counts["bracket_avanzado"] = True
    except Exception:
        counts["bracket_avanzado"] = False  # no-fatal: fixture cargado igual

    return {"ok": True, "torneo_id": torneo_id, **counts}


@router.patch("/fases/{fase_id}", summary="Actualizar visibilidad de fase para apostadores")
async def patch_fase(_: CurrentUser, fase_id: int, db: DBSession, visible_apostador: bool) -> dict:
    r = await db.execute(
        text("UPDATE fase SET visible_apostador=:v WHERE id=:fid RETURNING id, nombre, visible_apostador"),
        {"v": visible_apostador, "fid": fase_id}
    )
    row = r.mappings().one_or_none()
    if not row:
        raise HTTPException(404, "Fase no encontrada")
    await db.commit()
    return dict(row)


@router.get("/torneos/{torneo_id}/fixture", summary="Fixture completo del torneo")
async def get_fixture(torneo_id: int, db: DBSession) -> dict:
    """
    Devuelve todas las fases con sus partidos.
    Para fase de grupos incluye standings. Para playoffs incluye bracket.
    """
    # Fases del torneo ordenadas
    r = await db.execute(
        text("""
            SELECT id, nombre, tipo, orden,
                   COALESCE(visible_apostador, true) AS visible_apostador
            FROM fase
            WHERE torneo_id=:tid
            ORDER BY orden, nombre
        """),
        {"tid": torneo_id}
    )
    fases = [dict(row) for row in r.mappings()]

    # Partidos con datos de equipos
    r2 = await db.execute(
        text("""
            SELECT
                p.id, p.fase_id, p.jornada, p.fecha, p.sede, p.ciudad,
                p.goles_local, p.goles_visitante,
                p.goles_local_prorroga, p.goles_visitante_prorroga,
                p.penales_local, p.penales_visitante,
                p.estado, p.leg, p.partido_ida_id, p.api_fixture_id,
                COALESCE(p.numero_fifa, 0) AS numero_fifa,
                el.id    AS local_id,
                el.nombre AS local_nombre,
                el.nombre_es AS local_nombre_es,
                el.logo_url  AS local_logo,
                ev.id    AS visit_id,
                ev.nombre AS visit_nombre,
                ev.nombre_es AS visit_nombre_es,
                ev.logo_url  AS visit_logo
            FROM partido p
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.torneo_id=:tid
            ORDER BY p.fase_id, p.jornada, p.fecha NULLS LAST
        """),
        {"tid": torneo_id}
    )
    partidos = [dict(row) for row in r2.mappings()]

    # Agrupar partidos por fase_id
    from collections import defaultdict
    partidos_por_fase: dict[int, list] = defaultdict(list)
    for p in partidos:
        partidos_por_fase[p["fase_id"]].append(p)

    # Para cada fase tipo grupo, cargar standings
    r3 = await db.execute(
        text("""
            SELECT
                pa.fase_id, pa.posicion, pa.pj, pa.pg, pa.pe, pa.pp,
                pa.gf, pa.gc, pa.pts, pa.clasifica,
                e.id AS equipo_id, e.nombre, e.nombre_es, e.logo_url
            FROM participacion pa
            JOIN equipo e ON e.id = pa.equipo_id
            JOIN fase f ON f.id = pa.fase_id
            WHERE f.torneo_id=:tid
            ORDER BY pa.fase_id, pa.posicion
        """),
        {"tid": torneo_id}
    )
    standings_rows = [dict(row) for row in r3.mappings()]
    standings_por_fase: dict[int, list] = defaultdict(list)
    for s in standings_rows:
        standings_por_fase[s["fase_id"]].append(s)

    result = []
    for fase in fases:
        fid = fase["id"]
        result.append({
            **fase,
            "partidos": partidos_por_fase.get(fid, []),
            "standings": standings_por_fase.get(fid, []) if fase["tipo"] == "grupo" else [],
        })

    return {"torneo_id": torneo_id, "fases": result}


@router.get("/partidos/{partido_id}/estadisticas", summary="Estadísticas de un partido")
async def get_estadisticas(partido_id: int, db: DBSession) -> dict:
    """
    Devuelve estadísticas (de BD si existen) y eventos del partido.
    Si no hay estadísticas en BD, las carga desde la API automáticamente.
    """
    # Verificar si ya tenemos estadísticas
    r = await db.execute(
        text("SELECT COUNT(*) FROM partido_estadistica WHERE partido_id=:pid"),
        {"pid": partido_id}
    )
    tiene_stats = r.scalar() > 0

    if not tiene_stats:
        try:
            await torneo_service.cargar_estadisticas_partido(engine, partido_id)
        except Exception as e:
            # Si falla la API devolvemos lo que tengamos
            pass

    # Estadísticas estructuradas
    r2 = await db.execute(
        text("""
            SELECT
                ps.equipo_id, ps.tiros_total, ps.tiros_al_arco, ps.posesion,
                ps.pases_total, ps.pases_precision, ps.faltas,
                ps.tarjetas_amarillas, ps.tarjetas_rojas,
                ps.fueras_de_juego, ps.corners, ps.datos_extra,
                e.nombre, e.nombre_es, e.logo_url
            FROM partido_estadistica ps
            JOIN equipo e ON e.id = ps.equipo_id
            WHERE ps.partido_id=:pid
        """),
        {"pid": partido_id}
    )
    estadisticas = [dict(row) for row in r2.mappings()]

    # Eventos
    r3 = await db.execute(
        text("""
            SELECT
                pe.tipo, pe.minuto, pe.minuto_extra,
                pe.jugador_nombre, pe.asistencia_nombre, pe.detalle,
                e.id AS equipo_id, e.nombre AS equipo_nombre, e.logo_url
            FROM partido_evento pe
            LEFT JOIN equipo e ON e.id = pe.equipo_id
            WHERE pe.partido_id=:pid
            ORDER BY pe.minuto, pe.minuto_extra NULLS LAST
        """),
        {"pid": partido_id}
    )
    eventos = [dict(row) for row in r3.mappings()]

    # Datos básicos del partido
    r4 = await db.execute(
        text("""
            SELECT
                p.fecha, p.sede, p.ciudad,
                p.goles_local, p.goles_visitante,
                p.goles_local_prorroga, p.goles_visitante_prorroga,
                p.penales_local, p.penales_visitante,
                p.estado,
                el.nombre AS local_nombre, el.logo_url AS local_logo,
                ev.nombre AS visit_nombre, ev.logo_url AS visit_logo
            FROM partido p
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE p.id=:pid
        """),
        {"pid": partido_id}
    )
    partido_row = r4.mappings().one_or_none()
    partido_info = dict(partido_row) if partido_row else {}

    return {
        "partido_id": partido_id,
        "partido": partido_info,
        "estadisticas": estadisticas,
        "eventos": eventos,
    }
