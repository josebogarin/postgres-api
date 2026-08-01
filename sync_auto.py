"""
sync_auto.py - Sync automatico MULTI-TORNEO de resultados desde API-Football.

Corre CADA MINUTO con Windows Task Scheduler. En cada corrida:
  1. Obtiene la lista de torneos ACTIVOS (no cerrados, no terminados) desde
     GET /torneo/activas.
  2. Para CADA torneo activo:
       - propaga el bracket (sin costo de API),
       - si hay un partido activo POR FECHA/HORA (ventana 15 min antes -> 300 min
         despues del horario, o estado 'en_juego'), sincroniza resultados,
       - cada CATCHUP_INTERVAL ciclos corre catch-up (finalizados sin puntaje o
         con stats faltantes),
       - ESPN verify de los que recien finalizaron.
  Solo llama a API-Football cuando un partido esta en ventana activa -> no gasta
  cuota en dias/torneos sin partidos.

Registrar en Task Scheduler: bat\re_registrar_task.bat (o POST /scheduler-start).
La tarea NO tiene torneo fijo: descubre los torneos activos en cada corrida.
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error

# -- CONFIG -------------------------------------------------------------------

from becbuc_config import BASE_URL, ADMIN_USER, ADMIN_PASS
MAX_DETALLE      = 10    # max llamadas individuales a API-Football por torneo/ejecucion
FORCE            = False # True = re-sincroniza aunque el partido ya este 'finalizado'
CATCHUP_INTERVAL = 5     # correr catch-up cada N ciclos (cada ~5 minutos)
CATCHUP_WARN_MIN = 30    # advertir si el catch-up no corrio en mas de N minutos

_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_FILE    = os.path.join(_ROOT, "sync_auto.log")
STATE_FILE  = os.path.join(_ROOT, "sync_state.json")

# -- Logging ------------------------------------------------------------------

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync_auto")


# -- HTTP helper --------------------------------------------------------------

def _request(method: str, url: str, data: dict | None = None, token: str | None = None) -> dict:
    body    = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"HTTP {e.code} en {url}: {body_txt}")


# -- Auth ---------------------------------------------------------------------

def get_token() -> str:
    r = _request("POST", f"{BASE_URL}/api/v1/auth/login",
                 data={"username": ADMIN_USER, "password": ADMIN_PASS})
    token = r.get("access_token")
    if not token:
        raise RuntimeError(f"Login fallo: {r}")
    return token


# -- Torneos activos ----------------------------------------------------------

def get_torneos_activos(token: str) -> list[dict]:
    """Lista de torneos que NO estan cerrados ni terminados (deben seguir sync)."""
    r = _request("GET", f"{BASE_URL}/api/v1/torneo/activas", token=token)
    activos: list[dict] = []
    for t in (r if isinstance(r, list) else []):
        if t.get("cerrado"):
            continue
        if t.get("estado_juego") == "terminada":
            continue
        activos.append({"id": t["id"], "nombre": t.get("nombre", "?")})
    return activos


# -- Operaciones por torneo ---------------------------------------------------

def hay_partido_activo(token: str, tid: int) -> tuple[bool, list[dict]]:
    """Consulta si hay algun partido activo o por empezar (por fecha/hora)."""
    r = _request("GET", f"{BASE_URL}/api/v1/bets/hay-partido-activo/{tid}", token=token)
    return r.get("activo", False), r.get("partidos", [])


def run_sync(token: str, tid: int) -> dict:
    qs = f"?max_detalle={MAX_DETALLE}"
    if FORCE:
        qs += "&force=true"
    return _request("POST", f"{BASE_URL}/api/v1/bets/sync-resultados/{tid}{qs}", token=token)


def run_avanzar_bracket(token: str, tid: int) -> dict:
    """Propaga ganadores al siguiente round. Sin llamadas API-Football."""
    return _request("POST", f"{BASE_URL}/api/v1/bets/avanzar-bracket/{tid}", token=token)


def run_catchup(token: str, tid: int) -> dict:
    """Detecta partidos finalizados sin puntaje o con stats faltantes y los synca."""
    return _request("POST", f"{BASE_URL}/api/v1/bets/auto-catchup/{tid}", token=token)


def run_espn_verify(token: str, partido_id: int) -> dict:
    """Corrige VAR/amarillas/rojas/minuto de un partido recien finalizado."""
    return _request("GET", f"{BASE_URL}/api/v1/bets/espn-verify/{partido_id}", token=token)


# -- Estado persistente -------------------------------------------------------

def load_state() -> dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        log.warning(f"No se pudo guardar state: {e}")


# -- Procesar un torneo -------------------------------------------------------

def process_torneo(token: str, tid: int, nombre: str, tstate: dict, do_catchup: bool) -> dict:
    """Procesa un torneo. Devuelve el estado actualizado (en_juego_ids)."""
    prefix = f"[T{tid} {nombre}]"

    # Propagar bracket siempre (sin API-Football, solo DB).
    try:
        run_avanzar_bracket(token, tid)
    except Exception as e:
        log.warning(f"{prefix} avanzar-bracket fallo: {e}")

    prev_en_juego: set[int] = set(tstate.get("en_juego_ids", []))

    try:
        activo, partidos = hay_partido_activo(token, tid)
    except Exception as e:
        log.error(f"{prefix} chequeo partido activo fallo: {e}")
        return tstate  # sin cambios

    current_en_juego: set[int] = {p["id"] for p in partidos if p.get("estado") == "en_juego"}
    just_finalized: set[int]   = prev_en_juego - current_en_juego
    tstate["en_juego_ids"]     = list(current_en_juego)

    # Catch-up periodico (finalizados sin puntaje / stats faltantes).
    if do_catchup:
        try:
            cu    = run_catchup(token, tid)
            count = cu.get("catchup_count", 0)
            if count > 0:
                log.info(f"{prefix} Catch-up: {count} partido(s), "
                         f"{cu.get('api_calls', 0)} API calls, puntajes_ok={cu.get('puntajes_ok', False)}")
        except Exception as e:
            log.warning(f"{prefix} Catch-up fallo: {e}")

    # Si hay partido activo -> sincronizar.
    if activo:
        nombres = [f"{p.get('local_nombre','?')} vs {p.get('visitante_nombre','?')} [{p.get('estado','?')}]"
                   for p in partidos]
        log.info(f"{prefix} Activo(s) ({len(partidos)}): {' | '.join(nombres)} -> sync")
        try:
            result = run_sync(token, tid)
            sync   = result.get("sync", {})
            log.info(f"{prefix} Sync OK: {sync.get('actualizados', 0)} act, "
                     f"{sync.get('sin_match_api', 0)} sin match, {sync.get('api_calls', 0)} API calls, "
                     f"errores={sync.get('errores', 0)}, puntajes_ok={result.get('puntajes_ok', False)}")
            for e in sync.get("ids_errores", []):
                log.warning(f"{prefix}  Error partido {e.get('partido_id')}: {e.get('error')}")
            # re-chequear si alguno finalizo durante el sync
            try:
                _, partidos_post = hay_partido_activo(token, tid)
                post_en_juego = {p["id"] for p in partidos_post if p.get("estado") == "en_juego"}
                just_finalized |= (current_en_juego - post_en_juego)
                tstate["en_juego_ids"] = list(post_en_juego)
            except Exception as e:
                log.warning(f"{prefix} re-chequeo post-sync fallo: {e}")
        except Exception as e:
            log.error(f"{prefix} Sync fallido: {e}")
    elif not just_finalized:
        log.info(f"{prefix} Sin partido activo en ventana.")

    # ESPN verify para los que recien finalizaron.
    for pid in just_finalized:
        try:
            espn_r = run_espn_verify(token, pid)
            log.info(f"{prefix} ESPN verify P{pid}: correcciones={espn_r.get('correcciones', 0)} ok={espn_r.get('ok', False)}")
        except Exception as e:
            log.warning(f"{prefix} ESPN verify P{pid} fallo (se reintentara): {e}")

    return tstate


# -- Main ---------------------------------------------------------------------

def main():
    # 1. Login
    try:
        token = get_token()
    except Exception as e:
        log.error(f"Login fallido: {e}")
        sys.exit(1)

    # 2. Estado + contador de ciclo
    state       = load_state()
    cycle_count = state.get("cycle_count", 0) + 1
    do_catchup  = (cycle_count % CATCHUP_INTERVAL == 0)

    if do_catchup:
        last_ts = state.get("last_catchup_ts", 0)
        if last_ts and (time.time() - last_ts) / 60 > CATCHUP_WARN_MIN:
            log.warning(f"[WARN] Catch-up no corrio en mas de {CATCHUP_WARN_MIN} min - revisar scheduler")

    # 3. Descubrir torneos activos
    try:
        torneos = get_torneos_activos(token)
    except Exception as e:
        log.error(f"No se pudo obtener torneos activos: {e}")
        sys.exit(1)

    if not torneos:
        log.info("Sin torneos activos. Nada que sincronizar.")
        save_state({**state, "cycle_count": cycle_count})
        return

    # 4. Procesar cada torneo
    tor_state: dict = state.get("torneos", {})
    for t in torneos:
        tid = t["id"]
        key = str(tid)
        tor_state[key] = process_torneo(token, tid, t["nombre"], tor_state.get(key, {}), do_catchup)

    # 5. Guardar estado
    new_state = {
        "cycle_count":     cycle_count,
        "torneos":         tor_state,
        "last_catchup_ts": time.time() if do_catchup else state.get("last_catchup_ts", 0),
    }
    save_state(new_state)


if __name__ == "__main__":
    main()
