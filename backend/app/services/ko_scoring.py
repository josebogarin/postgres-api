"""
ko_scoring.py
=============
Lógica del bracket REAL único y la puntuación por fase con doblaje.

Modelo: todos los apostadores pronostican los MISMOS partidos reales del fixture.
A medida que se simula/cargan resultados reales, el bracket avanza (ganador/perdedor
de cada partido alimenta el siguiente) y los puntos se acumulan por fase.

Doblaje de puntos por fase (marcador Y bonus):
    grupo=1  ronda32=2  ronda16=4  cuartos=8  semis=16  tercer_puesto=16  final=32
"""

from __future__ import annotations

from sqlalchemy import text

# ── Multiplicador por tipo de fase ────────────────────────────────────────────
PHASE_MULT: dict[str, int] = {
    "grupo":         1,
    "ronda32":       2,
    "ronda16":       4,
    "cuartos":       8,
    "semis":         16,
    "tercer_puesto": 16,
    "final":         32,
}

# ── Rango de números de partido por tipo (orden oficial FIFA 2026) ────────────
# Los partidos de cada fase se mapean a estos números ordenando por id ascendente.
TIPO_NUM_RANGE: dict[str, list[int]] = {
    "ronda32":       list(range(73, 89)),   # 73-88 (16)
    "ronda16":       list(range(89, 97)),   # 89-96 (8)
    "cuartos":       list(range(97, 101)),  # 97-100 (4)
    "semis":         [101, 102],
    "tercer_puesto": [103],
    "final":         [104],
}

# ── Árbol de avance del bracket (match → (origen_local, origen_visitante)) ────
# ("W", n) = ganador del partido n ; ("L", n) = perdedor del partido n
# R32 (73-88) se arma desde standings de grupos, no tiene feeders aquí.
KO_FEEDERS: dict[int, tuple[tuple[str, int], tuple[str, int]]] = {
    # Octavos (R16)
    # NOTA: Los números BECBUC P73-P88 SÍ coinciden 1:1 con los números oficiales FIFA.
    # Verificado jun-2026 contra BD real:
    #   P73=South Africa/Canada  P74=Germany/Paraguay  P75=Netherlands/Morocco
    #   P76=Brazil/Japan  P77=France/Sweden  P78=Ivory Coast/Norway
    #   P79=Mexico/Ecuador  P80=England/Congo DR  P81=USA/Bosnia
    #   P82=Belgium/Senegal  P83=Portugal/Croatia  P84=Spain/Austria
    #   P85=Switzerland/Algeria  P86=Argentina/Cape Verde  P87=Colombia/Ghana  P88=Australia/Egypt
    89: (("W", 74), ("W", 77)),   # Germany/Paraguay vs France/Sweden
    90: (("W", 73), ("W", 75)),   # South Africa/Canada vs Netherlands/Morocco
    91: (("W", 76), ("W", 78)),   # Brazil/Japan vs Ivory Coast/Norway
    92: (("W", 79), ("W", 80)),   # Mexico/Ecuador vs England/Congo DR
    93: (("W", 83), ("W", 84)),   # Portugal/Croatia vs Spain/Austria
    94: (("W", 81), ("W", 82)),   # USA/Bosnia vs Belgium/Senegal
    95: (("W", 86), ("W", 88)),   # Argentina/Cape Verde vs Australia/Egypt
    96: (("W", 85), ("W", 87)),   # Switzerland/Algeria vs Colombia/Ghana
    # Cuartos
    97:  (("W", 89), ("W", 90)),
    98:  (("W", 93), ("W", 94)),
    99:  (("W", 91), ("W", 92)),
    100: (("W", 95), ("W", 96)),
    # Semis
    101: (("W", 97), ("W", 98)),
    102: (("W", 99), ("W", 100)),
    # Tercer puesto y Final
    103: (("L", 101), ("L", 102)),
    104: (("W", 101), ("W", 102)),
}


def winner_loser(p: dict) -> tuple[int | None, int | None]:
    """Devuelve (ganador_id, perdedor_id) de un partido finalizado de KO.

    Usa goles; si hay empate, define por penales. Devuelve (None, None) si no
    se puede determinar (sin equipos o sin resultado)."""
    lid, vid = p.get("equipo_local_id"), p.get("equipo_visitante_id")
    gl, gv = p.get("goles_local"), p.get("goles_visitante")
    if lid is None or vid is None or gl is None or gv is None:
        return (None, None)
    if gl > gv:
        return (lid, vid)
    if gv > gl:
        return (vid, lid)
    # Empate → penales
    pl, pv = p.get("penales_local"), p.get("penales_visitante")
    if pl is not None and pv is not None and pl != pv:
        return (lid, vid) if pl > pv else (vid, lid)
    return (None, None)


async def build_num_maps(db, torneo_id: int) -> dict:
    """Construye los mapeos número↔partido para las fases KO del torneo.

    Retorna: {num2pid, pid2num, num2tipo, fase_de_tipo:{tipo:fase_id}}"""
    r = await db.execute(
        text("""
            SELECT f.id AS fase_id, f.tipo, p.id AS pid
            FROM fase f
            JOIN partido p ON p.fase_id = f.id
            WHERE f.torneo_id = :tid AND f.tipo <> 'grupo'
            ORDER BY f.orden, p.id
        """),
        {"tid": torneo_id},
    )
    por_tipo: dict[str, list[int]] = {}
    fase_de_tipo: dict[str, int] = {}
    for row in r.mappings():
        por_tipo.setdefault(row["tipo"], []).append(row["pid"])
        fase_de_tipo[row["tipo"]] = row["fase_id"]

    num2pid: dict[int, int] = {}
    pid2num: dict[int, int] = {}
    num2tipo: dict[int, str] = {}
    for tipo, nums in TIPO_NUM_RANGE.items():
        pids = por_tipo.get(tipo, [])
        for num, pid in zip(nums, pids):
            num2pid[num] = pid
            pid2num[pid] = num
            num2tipo[num] = tipo
    return {"num2pid": num2pid, "pid2num": pid2num,
            "num2tipo": num2tipo, "fase_de_tipo": fase_de_tipo}


_TBD_ID_CACHE: int | None = None


async def _tbd_id(db) -> int:
    """Id del equipo placeholder 'Por Definir' (nombre='TBD'). Cacheado."""
    global _TBD_ID_CACHE
    if _TBD_ID_CACHE is None:
        r = await db.execute(text("SELECT id FROM equipo WHERE nombre = 'TBD' LIMIT 1"))
        row = r.first()
        _TBD_ID_CACHE = int(row[0]) if row else None
    return _TBD_ID_CACHE


async def _set_teams(db, pid: int, local_id: int | None, visit_id: int | None):
    """Asigna equipos a un partido KO con auto-corrección (self-heal).

    El bracket es función pura de los resultados actuales: cuando un feeder
    cambia de ganador, este partido debe reflejarlo aunque ya estuviera
    finalizado con OTROS equipos.

    - Si algún equipo es None -> no escribe (caller pasa TBD si quiere placeholder).
    - Si los equipos almacenados son IGUALES a los nuevos -> no-op (preserva el
      resultado ya jugado).
    - Si DIFIEREN -> reasigna equipos, limpia el resultado de ESTE partido
      (estado='programado', goles/prórroga/penales/min/amarillas/var = NULL) y
      pone en cero los puntos de las apuestas de este partido. Así las rondas
      profundas obsoletas se auto-corrigen en cascada."""
    if local_id is None or visit_id is None:
        return
    r = await db.execute(
        text("SELECT equipo_local_id, equipo_visitante_id, estado FROM partido WHERE id = :pid"),
        {"pid": pid},
    )
    row = r.mappings().first()
    if row is None:
        return
    if row["equipo_local_id"] == local_id and row["equipo_visitante_id"] == visit_id:
        return  # sin cambios: conserva el resultado existente
    # Partidos ya FINALIZADOS no se tocan: el resultado es canónico.
    # avanzar_ronda32 puede calcular local/visitante en orden diferente al oficial,
    # lo que borraría el resultado de un partido ya jugado.
    if row["estado"] == "finalizado":
        return
    # Los equipos cambiaron y el partido NO está finalizado -> reasignar y limpiar
    await db.execute(
        text("""
            UPDATE partido
            SET equipo_local_id = :l, equipo_visitante_id = :v,
                estado = 'programado',
                goles_local = NULL, goles_visitante = NULL,
                goles_local_prorroga = NULL, goles_visitante_prorroga = NULL,
                penales_local = NULL, penales_visitante = NULL,
                minuto_primer_gol = NULL, amarillas = NULL, decisiones_var = NULL
            WHERE id = :pid
        """),
        {"l": local_id, "v": visit_id, "pid": pid},
    )
    await db.execute(
        text("UPDATE apuesta SET puntos = 0, puntos_bonus = 0 WHERE partido_id = :pid"),
        {"pid": pid},
    )


async def avanzar_ronda32(db, torneo_id: int, num2pid: dict[int, int],
                          standings: dict, mejores_terceros: list[dict]) -> int:
    """Asigna equipos a los 16 partidos de R32 desde standings reales de grupos."""
    from app.services.bracket_service import armar_ronda32
    matches = armar_ronda32(standings, mejores_terceros)
    tbd = await _tbd_id(db)
    n = 0
    for m in matches:
        pid = num2pid.get(m["num"])
        if not pid:
            continue
        lid = (m["local"] or {}).get("equipo_id")
        vid = (m["visitante"] or {}).get("equipo_id")
        # Clasificado aún no resuelto -> TBD (self-heal en cascada).
        if lid is None:
            lid = tbd
        if vid is None:
            vid = tbd
        await _set_teams(db, pid, lid, vid)
        n += 1
    return n


async def avanzar_fase_ko(db, torneo_id: int, tipo: str, maps: dict) -> int:
    """Asigna equipos a los partidos de una fase KO (R16+) según ganadores/
    perdedores de la fase anterior. Requiere que la fase previa esté finalizada."""
    num2pid = maps["num2pid"]
    nums = TIPO_NUM_RANGE[tipo]

    # Cargar resultados de todos los partidos KO ya finalizados
    r = await db.execute(
        text("""
            SELECT p.id, p.equipo_local_id, p.equipo_visitante_id,
                   p.goles_local, p.goles_visitante,
                   p.penales_local, p.penales_visitante
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            WHERE f.torneo_id = :tid AND f.tipo <> 'grupo'
        """),
        {"tid": torneo_id},
    )
    res_por_num: dict[int, dict] = {}
    pid2num = maps["pid2num"]
    for row in r.mappings():
        num = pid2num.get(row["id"])
        if num is not None:
            res_por_num[num] = dict(row)

    tbd = await _tbd_id(db)
    n = 0
    for num in nums:
        feeders = KO_FEEDERS.get(num)
        if not feeders:
            continue
        (sl_tipo, sl_num), (sv_tipo, sv_num) = feeders
        pl = res_por_num.get(sl_num)
        pv = res_por_num.get(sv_num)
        lid = vid = None
        if pl:
            w, l = winner_loser(pl)
            lid = w if sl_tipo == "W" else l
        if pv:
            w, l = winner_loser(pv)
            vid = w if sv_tipo == "W" else l
        # Feeder no resuelto -> placeholder TBD para que rondas profundas
        # obsoletas se limpien en cascada (no se quedan con equipos viejos).
        if lid is None:
            lid = tbd
        if vid is None:
            vid = tbd
        pid = num2pid.get(num)
        if pid:
            await _set_teams(db, pid, lid, vid)
            n += 1
    return n
