# -*- coding: utf-8 -*-
"""
recalc_force_grupos.py
Recalcula los puntajes de TODO el torneo desde los DATOS ACTUALES de la BD,
incluyendo las fases BLOQUEADAS (grupos, 16avos, octavos, cuartos, semis).

Usa POST /calcular-puntajes/2?force_grupos=true, que:
  - Borra y recalcula puntaje_detalle de TODAS las fases (bloqueadas o no).
  - Salta el auto-lock de grupos.
  - NO cambia el estado de bloqueo de ninguna fase.

Esto corrige cualquier item que haya quedado STALE en fases bloqueadas:
  - N (minuto 1er gol): re-corre el desempate con el minuto real actual
    (ej. P064: AAA y MORO acertaron 28 en pleno, ahora reciben el punto).
  - L (VAR), y cualquier otro item que dependa de datos del partido.

Requiere uvicorn en :8000.

Uso:
  backend\\.venv\\Scripts\\python.exe recalc_force_grupos.py
"""
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests

API_BASE  = "http://localhost:8000/api/v1"
API_USER  = "jose"
API_PASS  = "catalina"
TORNEO_ID = 2

print("=" * 64)
print("BECBUC - Recalculo FORZADO de TODO el torneo (force_grupos=true)")
print("=" * 64)

# Login
print("\n== Login ==")
lr = requests.post(f"{API_BASE}/auth/login",
                   json={"username": API_USER, "password": API_PASS}, timeout=30)
tok = lr.json().get("access_token", "")
if not tok:
    sys.exit(f"login sin token -> {lr.status_code} {lr.text[:200]}")
hdr = {"Authorization": f"Bearer {tok}"}
print("  OK")

# Recalcular con force_grupos=true
print("\n== POST /calcular-puntajes/2?force_grupos=true ==")
cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}",
                   headers=hdr, params={"force_grupos": "true"}, timeout=600)
cd = cr.json()
if not cd.get("ok"):
    sys.exit(f"calcular-puntajes no OK -> {cd}")
print(f"  OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  fallos={cd.get('fallos')}")
for fase, d in (cd.get("por_fase") or {}).items():
    print(f"    [{fase:<14}] marcador={d.get('marcador',0):>5} bonus={d.get('bonus',0):>5}"
          f" total={d.get('total',0):>6} apuestas={d.get('apuestas',0):>4}")
print(f"  globales_procesadas={cd.get('globales_procesadas')}")
print(f"  grupos_auto_bloqueadas={cd.get('grupos_auto_bloqueadas', 0)} (debe ser 0 con force)")

# Ranking top-10
print("\n== Top 10 Ranking ==")
try:
    rr = requests.get(f"{API_BASE}/bets/ranking/{TORNEO_ID}", headers=hdr, timeout=30)
    _rj = rr.json()
    _rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
    for i, ap in enumerate(_rows[:10], 1):
        nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
        print(f"  {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
              f"(partidos={ap.get('puntos_partidos_total',0)}, globales={ap.get('pts_globales',0)})")
except Exception as e:
    print(f"  Error ranking: {e}")

print("\nListo. Recalculo forzado completo. El estado de bloqueo NO se modifico.")
