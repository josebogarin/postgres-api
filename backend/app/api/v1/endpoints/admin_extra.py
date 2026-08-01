"""Endpoint temporal: registrar BECBUC-SyncAPI en Task Scheduler. v2"""
import subprocess

from fastapi import APIRouter

from app.api.deps import CurrentAdmin

router = APIRouter()


@router.post("/register-sync-task")
async def register_sync_task(_admin: CurrentAdmin):
    """Registra o re-registra la tarea BECBUC-SyncAPI en Windows Task Scheduler."""
    import os as _os
    bat_path = _os.path.join(_os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..", "..")), "run_sync_auto.bat")
    results = {}

    r1 = subprocess.run(
        ["schtasks", "/delete", "/tn", "BECBUC-SyncAPI", "/f"],
        capture_output=True, text=True,
    )
    results["delete"] = r1.returncode

    r2 = subprocess.run(
        [
            "schtasks", "/create",
            "/tn", "BECBUC-SyncAPI",
            "/tr", bat_path,
            "/sc", "MINUTE",
            "/mo", "1",
            "/rl", "HIGHEST",
            "/f",
        ],
        capture_output=True, text=True,
    )
    results["create_stdout"] = r2.stdout.strip()
    results["create_stderr"] = r2.stderr.strip()
    results["create_rc"] = r2.returncode

    if r2.returncode == 0:
        r3 = subprocess.run(
            ["schtasks", "/run", "/tn", "BECBUC-SyncAPI"],
            capture_output=True, text=True,
        )
        results["run_rc"] = r3.returncode
        results["run_out"] = r3.stdout.strip()

    return {"ok": r2.returncode == 0, "results": results}
