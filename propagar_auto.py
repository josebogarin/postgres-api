# -*- coding: utf-8 -*-
"""
propagar_auto.py - Propagacion automatica del bracket de CLUBES.
Corre propagar_ganadores_clubes.py --apply para cada torneo de clubes activo.
Solo lee/escribe la BD (no llama a API-Football), es idempotente y barato.
Pensado para Windows Task Scheduler (cada ~5 min).

Registrar (PowerShell Admin):
  $action  = New-ScheduledTaskAction -Execute 'C:\\proyecto FAST API\\.venv\\Scripts\\python.exe' `
               -Argument 'C:\\proyecto FAST API\\propagar_auto.py' -WorkingDirectory 'C:\\proyecto FAST API'
  $trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 5) -Once -At (Get-Date)
  $settings= New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName 'BECBUC-PropagarClubes' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
"""
import subprocess, sys, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE, "propagar_ganadores_clubes.py")
LOG = os.path.join(BASE, "propagar_auto.log")
TORNEOS_CLUBES = [1, 14]   # Libertadores, Sudamericana

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")

def main():
    py = sys.executable
    for tid in TORNEOS_CLUBES:
        try:
            r = subprocess.run([py, SCRIPT, str(tid), "--apply"],
                               capture_output=True, text=True, timeout=120)
            out = (r.stdout or "").strip().splitlines()
            cambios = [l for l in out if "reemplaza" in l]
            if cambios:
                log(f"torneo {tid}: {len(cambios)} propagacion(es)")
                for c in cambios: log(f"   {c.strip()}")
            if r.returncode != 0:
                log(f"torneo {tid}: ERROR rc={r.returncode} {r.stderr[:200]}")
        except Exception as e:
            log(f"torneo {tid}: EXC {e}")

if __name__ == "__main__":
    main()
