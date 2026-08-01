"""
watchdog_becbuc.py — Watchdog del servidor BECBUC.

Lógica:
  1. Intenta conectar a http://localhost:8000/health (o raíz).
  2. Si el servidor ya responde → no hace nada (no levanta segunda instancia).
  3. Si no responde → inicia uvicorn en background.

Registrar en Windows Task Scheduler para que corra cada minuto:

    $action  = New-ScheduledTaskAction `
                 -Execute 'C:\proyecto FAST API\.venv\Scripts\pythonw.exe' `
                 -Argument 'C:\proyecto FAST API\watchdog_becbuc.py' `
                 -WorkingDirectory 'C:\proyecto FAST API'
    $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 1) -Once -At (Get-Date)
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName 'BECBUC-Watchdog' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest

    # Ver si está corriendo:
    Get-ScheduledTask -TaskName 'BECBUC-Watchdog' | Get-ScheduledTaskInfo

    # Eliminar:
    Unregister-ScheduledTask -TaskName 'BECBUC-Watchdog' -Confirm:$false
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))

import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_DIR    = _BASE
VENV_PYTHON = os.path.join(BASE_DIR, r".venv\Scripts\python.exe")
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
SERVER_URL  = "http://localhost:8000"
LOG_FILE    = os.path.join(BASE_DIR, "watchdog_becbuc.log")
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _server_alive() -> bool:
    """Devuelve True si el servidor ya está escuchando en el puerto 8000."""
    try:
        req = urllib.request.Request(SERVER_URL, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status < 500
    except Exception:
        return False


def _start_server() -> None:
    """Lanza uvicorn en background (proceso independiente, no bloquea)."""
    cmd = [
        VENV_PYTHON, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]
    log.info("Iniciando servidor: %s", " ".join(cmd))
    # DETACHED_PROCESS: el proceso sigue vivo al terminar este script
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        stdout=open(os.path.join(BASE_DIR, "server.log"), "a"),
        stderr=subprocess.STDOUT,
        close_fds=True,
    )


def main() -> None:
    if _server_alive():
        log.debug("Servidor OK — sin acción.")
        return

    log.warning("Servidor NO responde en %s — arrancando…", SERVER_URL)
    _start_server()
    log.info("Proceso uvicorn iniciado.")


if __name__ == "__main__":
    main()
