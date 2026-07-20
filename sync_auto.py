"""
sync_auto.py - Sync automatico de resultados desde API-Football.

LOGICA DE VENTANA:
  El script se programa para correr CADA MINUTO con Windows Task Scheduler.
  Solo llama a API-Football si hay un partido activo (ventana 15-300 min).

CATCH-UP AUTOMATICO (cada CATCHUP_INTERVAL ciclos = cada ~5 min):
  Detecta partidos finalizados sin puntaje calculado o con stats faltantes
  (decisiones_var IS NULL, minuto_primer_gol IS NULL) y los synca desde API.
  Garantiza que ningun partido quede sin calcular aunque la ventana temporal
  haya expirado o el servidor haya estado caido durante el partido.

Registrar en Task Scheduler (PowerShell como Administrador):
    $action  = New-ScheduledTaskAction `
                 -Execute 'C:\\proyecto FAST API\\.venv\\Scripts\\python.exe' `
                 -Argument 'C:\\proyecto FAST API\\sync_auto.py' `
                 -WorkingDirectory 'C:\\proyecto FAST API'
    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 1) -Once -At (Get-Date)
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName 'BECBUC-SyncAPI' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
"""

import json
import logging
import sys
import time
import urllib.request
import urllib.error

# -- CONFIG -------------------------------------------------------------------

from becbuc_config import TORNEO_ID, BASE_URL, ADMIN_USER, ADMIN_PASS
MAX_DETALLE      = 10    # max llamadas individuales a API-Football por ejecucion
FORCE            = False # True = re-sincroniza aunque el partido ya este 'finalizado'
CATCHUP_INTERVAL = 5     # correr catch-up cada N ciclos (cada ~5 minutos)
CATCHUP_WARN_MIN = 30    # advertir si el catch-up no corrio en mas de N minutos

LOG_FILE    = r"C:\proyecto FAST API\sync_auto.log"
STATE_FILE  = r"C:\proyecto FAST API\sync_state.json"

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


# -- Chequeo de partido activo ------------------------------------------------

def hay_partido_activo(token: str) -> tuple[bool, list[dict]]:
    """Consulta al servidor si hay algun partido activo o por empezar."""
    r = _request("GET", f"{BASE_URL}/api/v1/bets/hay-partido-activo/{TORNEO_ID}", token=token)
    return r.get("activo", False), r.get("partidos", [])


# -- Sync ---------------------------------------------------------------------

def run_sync(token: str) -> dict:
    qs = f"?max_detalle={MAX_DETALLE}"
    if FORCE:
        qs += "&force=true"
    return _request("POST", f"{BASE_URL}/api/v1/bets/sync-resultados/{TORNEO_ID}{qs}", token=token)


def run_avanzar_bracket(token: str) -> dict:
    """Propaga ganadores al siguiente round. Sin llamadas API-Football."""
    return _request("POST", f"{BASE_URL}/api/v1/bets/avanzar-bracket/{TORNEO_ID}", token=token)


def run_catchup(token: str) -> dict:
    """
    Llama a /auto-catchup: detecta partidos finalizados sin puntaje o con
    stats faltantes (decisiones_var, minuto_primer_gol) y los synca.
    Corre cada CATCHUP_INTERVAL ciclos sin importar si hay partido activo.
    """
    return _request("POST", f"{BASE_URL}/api/v1/bets/auto-catchup/{TORNEO_ID}", token=token)


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


def should_run_catchup(state: dict) -> bool:
    """Retorna True si toca correr el catch-up en este ciclo."""
    cycle = state.get("cycle_count", 0)
    return cycle % CATCHUP_INTERVAL == 0


def catchup_overdue(state: dict) -> bool:
    """Retorna True si el catch-up no corrio en mas de CATCHUP_WARN_MIN minutos."""
    last_ts = state.get("last_catchup_ts", 0)
    elapsed_min = (time.time() - last_ts) / 60
    return elapsed_min > CATCHUP_WARN_MIN


# -- ESPN verify (post-partido) -----------------------------------------------

def run_espn_verify(token: str, partido_id: int) -> dict:
    """Llama al endpoint ESPN verify para corregir VAR/amarillas/rojas/minuto."""
    return _request("GET", f"{BASE_URL}/api/v1/bets/espn-verify/{partido_id}", token=token)


# -- Main ---------------------------------------------------------------------

def main():
    # 1. Login
    try:
        token = get_token()
    except Exception as e:
        log.error(f"Login fallido: {e}")
        sys.exit(1)

    # 2. Cargar estado previo
    state = load_state()
    prev_en_juego: set[int] = set(state.get("en_juego_ids", []))
    cycle_count: int         = state.get("cycle_count", 0) + 1

    # 3. Verificar si hay partido activo
    try:
        activo, partidos = hay_partido_activo(token)
    except Exception as e:
        log.error(f"Error al chequear partido activo: {e}")
        sys.exit(1)

    # IDs actualmente en_juego
    current_en_juego: set[int] = {p["id"] for p in partidos if p.get("estado") == "en_juego"}

    # Partidos que estaban en_juego en el run anterior pero ya NO aparecen
    just_finalized: set[int] = prev_en_juego - current_en_juego

    # Guardar estado actualizado
    new_state = {
        "en_juego_ids":    list(current_en_juego),
        "cycle_count":     cycle_count,
        "last_catchup_ts": state.get("last_catchup_ts", 0),
    }
    save_state(new_state)

    # Propagar bracket siempre (sin API-Football, solo DB).
    try:
        br = run_avanzar_bracket(token)
        log.info(f"Bracket propagado: {br.get('mensaje', 'ok')}")
    except Exception as e:
        log.warning(f"avanzar-bracket fallo: {e}")

    # -- CATCH-UP periodico ---------------------------------------------------
    # Cada CATCHUP_INTERVAL ciclos: detecta partidos finalizados sin puntaje
    # o con stats faltantes. No depende de ventana activa.
    if should_run_catchup(new_state):
        if catchup_overdue(new_state):
            log.warning(
                f"[WARN] Catch-up no corrio en mas de {CATCHUP_WARN_MIN} min"
                " - posible problema con el scheduler"
            )
        try:
            cu       = run_catchup(token)
            count    = cu.get("catchup_count", 0)
            calls    = cu.get("api_calls", 0)
            pts_ok   = cu.get("puntajes_ok", False)
            err_list = cu.get("errors", [])
            if count > 0:
                log.info(
                    f"Catch-up: {count} partido(s) sync'd, "
                    f"{calls} API calls, puntajes_ok={pts_ok}"
                )
                for err in err_list:
                    log.warning(f"  Catch-up error {err.get('partido')}: {err.get('error')}")
            else:
                log.info("Catch-up: sin partidos pendientes")
            new_state["last_catchup_ts"] = time.time()
            save_state(new_state)
        except Exception as e:
            log.warning(f"Catch-up fallo: {e}")

    if not activo and not just_finalized:
        log.info("Sin partido activo en ventana. Nada que sincronizar.")
        return

    # 4. Hay partidos activos -> sincronizar
    if activo:
        nombres = [
            f"P{p.get('numero_fifa','?')} {p.get('local_nombre','?')} vs "
            f"{p.get('visitante_nombre','?')} [{p.get('estado','?')}]"
            for p in partidos
        ]
        log.info(f"Partido(s) activo(s) ({len(partidos)}): {' | '.join(nombres)} -> iniciando sync")

        try:
            result = run_sync(token)
        except Exception as e:
            log.error(f"Sync fallido: {e}")
            sys.exit(1)

        sync   = result.get("sync", {})
        act    = sync.get("actualizados", 0)
        yaf    = sync.get("ya_finalizados", 0)
        sm     = sync.get("sin_match_api", 0)
        err    = sync.get("errores", 0)
        calls  = sync.get("api_calls", 0)
        pts_ok = result.get("puntajes_ok", False)

        log.info(
            f"Sync OK: {act} actualizados, {yaf} ya tenian, {sm} sin match, "
            f"{calls} API calls, errores={err}, puntajes_ok={pts_ok}"
        )
        for e in sync.get("ids_errores", []):
            log.warning(f"  Error partido {e.get('partido_id')}: {e.get('error')}")

        # Detectar si algun partido en_juego finalizo durante el sync
        try:
            _, partidos_post = hay_partido_activo(token)
            post_en_juego = {p["id"] for p in partidos_post if p.get("estado") == "en_juego"}
            newly_finalized = current_en_juego - post_en_juego
            just_finalized |= newly_finalized
            if newly_finalized:
                save_state({**new_state, "en_juego_ids": list(post_en_juego)})
        except Exception as e:
            log.warning(f"No se pudo re-chequear partidos post-sync: {e}")

    # 5. ESPN verify para cada partido que acaba de finalizar
    for pid in just_finalized:
        log.info(f"Partido {pid} recien finalizado -> ESPN verify")
        try:
            espn_r = run_espn_verify(token, pid)
            corr   = espn_r.get("correcciones", 0)
            ok     = espn_r.get("ok", False)
            log.info(f"  ESPN verify P{pid}: correcciones={corr} ok={ok}")
        except Exception as e:
            log.warning(f"  ESPN verify P{pid} fallo (se reintentara): {e}")


if __name__ == "__main__":
    main()
