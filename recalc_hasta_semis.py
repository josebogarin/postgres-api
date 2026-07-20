# -*- coding: utf-8 -*-
"""
recalc_hasta_semis.py
Recalcula los puntajes de TODO el torneo HASTA SEMIS, incluso de las fases
BLOQUEADAS (grupos, 16avos, octavos, cuartos, semis).

Como POST /calcular-puntajes SALTA las fases bloqueadas, este script:
  1) Guarda el estado bloqueada de cada fase (excepto tercer_puesto y final).
  2) Desbloquea temporalmente todas esas fases.
  3) POST /calcular-puntajes/2 (recalcula todo lo que este finalizado).
  4) RESTAURA el estado de bloqueo original (siempre, incluso si algo falla).

No toca tercer_puesto ni final (aun sin resultado). Requiere uvicorn en :8000.

Uso:
  backend\.venv\Scripts\python.exe recalc_hasta_semis.py
"""
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2, psycopg2.extras
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2, psycopg2.extras

API_BASE  = "http://localhost:8000/api/v1"
API_USER  = "jose"
API_PASS  = "catalina"
TORNEO_ID = 2
CONN_BEC  = "host=localhost port=5432 dbname=becbuc user=app_user password=superpassword"
# fases que NO se tocan (aun sin jugarse / se manejan aparte)
EXCLUIR_TIPOS = ("tercer_puesto", "tercero", "final")

print("=" * 64)
print("BECBUC - Recalcular puntajes de TODO el torneo HASTA SEMIS")
print("=" * 64)

conn = psycopg2.connect(CONN_BEC)
conn.autocommit = True
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1) Estado actual de fases (las que vamos a recalcular)
cur.execute("""
    SELECT id, nombre, tipo, COALESCE(bloqueada, FALSE) AS bloqueada
    FROM fase
    WHERE torneo_id = %s AND lower(tipo) NOT IN %s
    ORDER BY id
""", (TORNEO_ID, EXCLUIR_TIPOS))
fases = cur.fetchall()
if not fases:
    conn.close(); sys.exit("No se hallaron fases para recalcular.")

bloqueadas_orig = [f['id'] for f in fases if f['bloqueada']]
print(f"\nFases a recalcular: {len(fases)}  (bloqueadas actualmente: {len(bloqueadas_orig)})")
for f in fases:
    print(f"  id={f['id']:>4} [{f['tipo']:<14}] {f['nombre']:<26} bloqueada={'SI' if f['bloqueada'] else 'no'}")

login_hdr = None
try:
    # 2) Desbloquear temporalmente
    print("\n== Desbloqueando fases temporalmente ==")
    cur.execute("""
        UPDATE fase SET bloqueada=FALSE
        WHERE torneo_id=%s AND lower(tipo) NOT IN %s
    """, (TORNEO_ID, EXCLUIR_TIPOS))
    print("  OK (todas desbloqueadas para el recalculo)")

    # 3) Login + recalcular
    print("\n== Login + POST /calcular-puntajes/2 ==")
    lr = requests.post(f"{API_BASE}/auth/login",
                       json={"username": API_USER, "password": API_PASS}, timeout=30)
    tok = lr.json().get("access_token", "")
    if not tok:
        raise RuntimeError(f"login sin token -> {lr.status_code} {lr.text[:200]}")
    login_hdr = {"Authorization": f"Bearer {tok}"}

    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}", headers=login_hdr, timeout=600)
    cd = cr.json()
    if not cd.get("ok"):
        raise RuntimeError(f"calcular-puntajes no OK -> {cd}")
    print(f"  OK  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  fallos={cd.get('fallos')}")
    for fase, d in (cd.get("por_fase") or {}).items():
        print(f"    [{fase}] marcador={d.get('marcador',0)} bonus={d.get('bonus',0)}"
              f" total={d.get('total',0)} apuestas={d.get('apuestas',0)}")
    print(f"  globales_procesadas={cd.get('globales_procesadas')}")

finally:
    # 4) Restaurar el bloqueo original SIEMPRE
    print("\n== Restaurando estado de bloqueo original ==")
    if bloqueadas_orig:
        cur.execute("UPDATE fase SET bloqueada=TRUE WHERE id = ANY(%s)", (bloqueadas_orig,))
        print(f"  Re-bloqueadas {len(bloqueadas_orig)} fases: {bloqueadas_orig}")
    else:
        print("  (ninguna estaba bloqueada; nada que restaurar)")

# 5) Ranking top-10
if login_hdr:
    print("\n== Top 10 Ranking ==")
    try:
        rr = requests.get(f"{API_BASE}/bets/ranking/{TORNEO_ID}", headers=login_hdr, timeout=30)
        _rj = rr.json()
        _rows = _rj.get("ranking", []) if isinstance(_rj, dict) else _rj
        for i, ap in enumerate(_rows[:10], 1):
            nombre = ap.get('apostador') or ap.get('username') or ap.get('nombre') or '?'
            print(f"  {i:>2}. {nombre:<20} {ap.get('puntos_total',0):>6} pts "
                  f"(partidos={ap.get('puntos_partidos_total',0)}, globales={ap.get('pts_globales',0)})")
    except Exception as e:
        print(f"  Error ranking: {e}")

conn.close()
print("\nListo. Puntajes recalculados hasta semis y bloqueo restaurado.")
