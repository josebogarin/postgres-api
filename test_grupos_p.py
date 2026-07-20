"""
test_grupos_p.py — Verifica el algoritmo de Item P (grupos clasificados a R32)
Requiere: uvicorn activo en puerto 8000

Ejecutar: cd "C:\proyecto FAST API" && backend\.venv\Scripts\python test_grupos_p.py
"""
import asyncio
import sys
import json
import psycopg2
from datetime import datetime

BECBUC_DSN = "host=localhost dbname=becbuc user=app_user"
API_BASE   = "http://localhost:8000"
TORNEO_ID  = 2

# ─── Login admin ────────────────────────────────────────────────────────────
def get_token():
    import urllib.request, urllib.parse
    payload = json.dumps({"username": "Jose", "password": "catalina"}).encode()
    req = urllib.request.Request(f"{API_BASE}/api/v1/auth/login",
                                 data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]

# ─── Llamar calcular-puntajes ────────────────────────────────────────────────
def calcular_puntajes(token):
    import urllib.request
    req = urllib.request.Request(
        f"{API_BASE}/api/v1/bets/calcular-puntajes/{TORNEO_ID}",
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

# ─── Consultar BD directamente ───────────────────────────────────────────────
def check_bd():
    conn = psycopg2.connect(BECBUC_DSN)
    cur  = conn.cursor()

    print("\n" + "═"*60)
    print("APOSTADOR_CLASIFICADOS — Grupos (bonus R32)")
    print("═"*60)

    cur.execute("""
        SELECT ac.apostador_id,
               ac.aciertos,
               ac.pts_por_acierto,
               ac.pts_obtenidos,
               array_length(ac.equipos_pronosticados, 1) AS n_pred,
               array_length(ac.equipos_reales, 1)        AS n_real,
               ac.calculado_at
          FROM apostador_clasificados ac
         WHERE ac.torneo_id = %s AND ac.fase_tipo = 'grupo'
         ORDER BY ac.pts_obtenidos DESC, ac.aciertos DESC
    """, (TORNEO_ID,))
    rows = cur.fetchall()

    if not rows:
        print("⚠  Sin datos. Corre calcular-puntajes primero.")
    else:
        print(f"{'ApostID':>8}  {'Pred':>4}  {'Real':>4}  {'Aciert':>6}  {'Pts/eq':>6}  {'Total':>5}  Calculado")
        print("-"*60)
        total_pts = 0
        for r in rows:
            aid, aciertos, ppa, pts, n_pred, n_real, calc_at = r
            print(f"{aid:>8}  {n_pred or 0:>4}  {n_real or 0:>4}  {aciertos:>6}  {ppa:>6}  {pts:>5}  {calc_at}")
            total_pts += pts
        print("-"*60)
        print(f"{'TOTAL':>8}  {'':>4}  {'':>4}  {'':>6}  {'':>6}  {total_pts:>5}")

    # Verificar que los equipos reales son los mismos para todos
    cur.execute("""
        SELECT DISTINCT equipos_reales
          FROM apostador_clasificados
         WHERE torneo_id = %s AND fase_tipo = 'grupo'
    """, (TORNEO_ID,))
    reales_rows = cur.fetchall()
    if len(reales_rows) > 1:
        print("\n⚠  INCONSISTENCIA: distintos apostadores tienen diferentes equipos_reales!")
    elif len(reales_rows) == 1:
        eq_reales = reales_rows[0][0]
        print(f"\n✅ equipos_reales consistentes: {len(eq_reales) if eq_reales else 0} equipos")

    # Verificar que ningún apostador tiene 0 equipos predichos (bug potencial)
    cur.execute("""
        SELECT COUNT(*) FROM apostador_clasificados
         WHERE torneo_id = %s AND fase_tipo = 'grupo'
           AND (equipos_pronosticados IS NULL OR array_length(equipos_pronosticados, 1) < 5)
    """, (TORNEO_ID,))
    bajo = cur.fetchone()[0]
    if bajo > 0:
        print(f"\n⚠  {bajo} apostadores con menos de 5 equipos predichos — posible bug en _get_apostador_predicted_r32")
    else:
        print(f"✅ Todos tienen ≥ 5 equipos predichos")

    # Mostrar los equipos reales con nombres
    print("\n" + "═"*60)
    print("EQUIPOS REALES EN R32 (según BD partido)")
    print("═"*60)
    cur.execute("""
        SELECT id, nombre FROM (
            SELECT DISTINCT e.id,
                   COALESCE(e.nombre_es, e.nombre) AS nombre
              FROM partido p
              JOIN fase f ON f.id = p.fase_id
              JOIN equipo e ON e.id = p.equipo_local_id
             WHERE f.torneo_id = %s
               AND (LOWER(f.tipo) = 'ronda32' OR LOWER(f.tipo) LIKE '%%ronda32%%')
               AND p.equipo_local_id IS NOT NULL AND p.equipo_local_id > 0
            UNION
            SELECT DISTINCT e.id, COALESCE(e.nombre_es, e.nombre)
              FROM partido p
              JOIN fase f ON f.id = p.fase_id
              JOIN equipo e ON e.id = p.equipo_visitante_id
             WHERE f.torneo_id = %s
               AND (LOWER(f.tipo) = 'ronda32' OR LOWER(f.tipo) LIKE '%%ronda32%%')
               AND p.equipo_visitante_id IS NOT NULL AND p.equipo_visitante_id > 0
        ) sub ORDER BY nombre
    """, (TORNEO_ID, TORNEO_ID))
    equipos = cur.fetchall()
    print(f"Total equipos en R32: {len(equipos)}")
    for row in equipos:
        eid, nombre = row[0], row[1]
        print(f"  {eid:>4}  {nombre}")

    # Verificar KO fases
    print("\n" + "═"*60)
    print("APOSTADOR_CLASIFICADOS — KO fases")
    print("═"*60)
    cur.execute("""
        SELECT fase_tipo, COUNT(*) AS n_apostadores,
               SUM(aciertos) AS total_aciertos,
               SUM(pts_obtenidos) AS total_pts
          FROM apostador_clasificados
         WHERE torneo_id = %s AND fase_tipo != 'grupo'
         GROUP BY fase_tipo ORDER BY fase_tipo
    """, (TORNEO_ID,))
    ko_rows = cur.fetchall()
    if ko_rows:
        for ft, n, aciertos, pts in ko_rows:
            print(f"  {ft:<15}  apostadores={n}  aciertos={aciertos}  pts={pts}")
    else:
        print("  (sin datos KO aún — normal si R32 no ha terminado)")

    conn.close()

# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Test Item P — Grupos clasificados a R32")
    print("Obteniendo token...")
    try:
        token = get_token()
        print(f"  ✅ Login OK")
    except Exception as e:
        print(f"  ❌ Login falló: {e}")
        sys.exit(1)

    print("Llamando POST /calcular-puntajes...")
    try:
        result = calcular_puntajes(token)
        clas_g  = result.get("clasificados_grupos", "N/A")
        clas_ko = result.get("clasificados_ko_fases", [])
        plenos   = result.get("plenos", "?")
        aciertos = result.get("aciertos", "?")
        print(f"  ✅ OK — plenos={plenos}, aciertos={aciertos}, grupos_p={clas_g} apostadores, ko_fases={clas_ko}")
    except Exception as e:
        print(f"  ❌ calcular-puntajes falló: {e}")
        print("  Verificando BD directamente...")

    print("\nConsultando BD...")
    try:
        check_bd()
    except Exception as e:
        print(f"  ❌ Error BD: {e}")
        print("  Asegurate de que PostgreSQL esté activo y accesible en localhost:5432")

if __name__ == "__main__":
    main()
