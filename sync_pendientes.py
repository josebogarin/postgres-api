"""
sync_pendientes.py - Barrido por FECHA/HORA, SOLO para los torneos habilitados
en el Live (torneo.mostrar_live=TRUE -> /torneo/activas?solo_live=true).

Para cada torneo del Live llama a POST /sync-pendientes/{tid}, que:
  - busca partidos cuyo horario ya paso y siguen sin resultado,
  - los sincroniza desde API-Football guardando todos los items en BD,
  - avanza bracket y recalcula puntajes.

Pensado para Task Scheduler CADA ~15 MIN (no cada minuto).
En dias sin partidos vencidos: 0 llamadas a API-Football.
"""
import json, logging, os, sys, urllib.request, urllib.error
from becbuc_config import BASE_URL, ADMIN_USER, ADMIN_PASS

MAX_DETALLE = 15
_ROOT = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(_ROOT, "sync_auto.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync_pendientes")


def req(method, url, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")


def main():
    try:
        tok = req("POST", f"{BASE_URL}/api/v1/auth/login",
                  data={"username": ADMIN_USER, "password": ADMIN_PASS}).get("access_token")
        if not tok:
            log.error("Login sin token"); sys.exit(1)
    except Exception as e:
        log.error(f"Login fallido: {e}"); sys.exit(1)

    try:
        activas = req("GET", f"{BASE_URL}/api/v1/torneo/activas?solo_live=true", token=tok)
    except Exception as e:
        log.error(f"No se pudo listar torneos del Live: {e}"); sys.exit(1)

    torneos = [t for t in (activas or []) if not t.get("cerrado")]
    if not torneos:
        log.info("Sin torneos habilitados en el Live. Nada que hacer.")
        return

    for t in torneos:
        tid = t["id"]
        nombre = t.get("nombre", "?")
        try:
            r = req("POST", f"{BASE_URL}/api/v1/bets/sync-pendientes/{tid}?max_detalle={MAX_DETALLE}", token=tok)
            pend = r.get("pendientes", 0)
            sync = r.get("sincronizados", 0)
            calls = r.get("api_calls", 0)
            if pend:
                log.info(f"[T{tid} {nombre}] pendientes={pend} sincronizados={sync} "
                         f"api_calls={calls} puntajes_ok={r.get('puntajes_ok')}")
                for e in r.get("errores", [])[:10]:
                    log.warning(f"[T{tid}]  err {e.get('partido')}: {e.get('error')}")
                if r.get("sin_fixture"):
                    log.warning(f"[T{tid}] sin api_fixture_id (falta mapeo): {r['sin_fixture']}")
            else:
                log.info(f"[T{tid} {nombre}] sin partidos pendientes por fecha")
        except Exception as e:
            log.error(f"[T{tid} {nombre}] sync-pendientes fallo: {e}")


if __name__ == "__main__":
    main()
