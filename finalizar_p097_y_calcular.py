# -*- coding: utf-8 -*-
"""
finalizar_p097_y_calcular.py
1) Sync forzado desde API-Football (intenta finalizar P097 France 2-0 Morocco)
2) Si P097 sigue en_juego, lo finaliza directamente en BD y via API
3) Recalcula puntajes
4) Muestra ranking
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

# ── Login ──────────────────────────────────────────────────────
try:
    lr = requests.post(f"{API_BASE}/auth/login",
                       json={"username": API_USER, "password": API_PASS}, timeout=30)
    tok = lr.json().get("access_token", "")
except Exception as e:
    sys.exit(f"ERROR login (uvicorn en :8000?): {e}")
if not tok:
    sys.exit(f"ERROR login sin token: {lr.status_code} {lr.text[:200]}")

hdr = {"Authorization": f"Bearer {tok}"}
print(f"✅ Login OK\n")

# ── 1. Ver estado de P097 en BD ───────────────────────────────
conn = psycopg2.connect(CONN_BEC)
conn.autocommit = True
cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT p.id, p.numero_fifa, p.estado, p.goles_local, p.goles_visitante,
           p.equipo_clasificado_id, p.api_fixture_id,
           COALESCE(p.datos_confirmados, FALSE) AS confirmado,
           el.nombre AS local, ev.nombre AS visitante,
           COALESCE(ec.nombre, 'sin definir') AS clasificado
    FROM partido p
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
    WHERE p.numero_fifa = 97 AND p.fase_id IN (
        SELECT id FROM fase WHERE torneo_id = %s AND tipo ILIKE 'cuartos'
    )
""", (TORNEO_ID,))
p97 = cur.fetchone()

if not p97:
    print("⚠️  P097 no encontrado en fase cuartos. Buscando por numero_fifa=97...")
    cur.execute("""
        SELECT p.id, p.numero_fifa, p.estado, p.goles_local, p.goles_visitante,
               p.api_fixture_id, el.nombre AS local, ev.nombre AS visitante
        FROM partido p
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.numero_fifa = 97
    """)
    p97 = cur.fetchone()

if p97:
    print(f"== Estado P097 ==")
    print(f"   DB id         : {p97['id']}")
    print(f"   {p97['local']} {p97['goles_local']}-{p97['goles_visitante']} {p97['visitante']}")
    print(f"   estado        : {p97['estado']}")
    print(f"   api_fixture_id: {p97['api_fixture_id']}")
    print(f"   clasificado   : {p97.get('clasificado','?')}")
    print(f"   confirmado    : {p97.get('confirmado','?')}")
else:
    print("❌ P097 no encontrado en BD")

# ── 2. Sync forzado desde API-Football ────────────────────────
print(f"\n== 2) Sync forzado desde API-Football ==")
try:
    sr = requests.post(f"{API_BASE}/bets/sync-resultados/{TORNEO_ID}?force=true",
                       headers=hdr, timeout=120)
    sd = sr.json()
    print(f"   HTTP {sr.status_code}")
    print(f"   actualizados     : {sd.get('actualizados', '?')}")
    print(f"   bracket_ok       : {sd.get('bracket_ok', '?')}")
    print(f"   puntajes_ok      : {sd.get('puntajes_ok', '?')}")
    for k in ('plenos','aciertos','fallos','por_fase','globales_procesadas'):
        if k in sd:
            print(f"   {k}: {sd[k]}")
except Exception as e:
    print(f"   ERROR sync: {e}")

# ── 3. Re-verificar P097 ──────────────────────────────────────
cur.execute("SELECT estado, goles_local, goles_visitante FROM partido WHERE id = %s",
            (p97['id'],))
p97_new = cur.fetchone()
print(f"\n== Estado P097 post-sync ==")
print(f"   estado: {p97_new['estado']}  goles: {p97_new['goles_local']}-{p97_new['goles_visitante']}")

# ── 4. Si sigue en_juego, finalizar via API ───────────────────
if p97_new['estado'] != 'finalizado':
    print(f"\n== 4) P097 aún '{p97_new['estado']}' → finalizando via API ==")
    # Usar goles que ya están en BD (2-0 France)
    gl = p97_new['goles_local']  or 2
    gv = p97_new['goles_visitante'] or 0
    try:
        fr = requests.post(
            f"{API_BASE}/bets/finalizar-partido/{p97['id']}?goles_local={gl}&goles_visitante={gv}",
            headers=hdr, timeout=60)
        fd = fr.json()
        print(f"   HTTP {fr.status_code}")
        print(f"   estado     : {fd.get('estado','?')}")
        print(f"   bracket_ok : {fd.get('bracket_ok','?')}")
        print(f"   puntajes_ok: {fd.get('puntajes_ok','?')}")
        # Mostrar puntajes si disponibles
        pts = fd.get('puntajes') or fd.get('puntajes_ok')
        if isinstance(pts, dict):
            for k,v in pts.items():
                print(f"   {k}: {v}")
    except Exception as e:
        print(f"   ERROR finalizar: {e}")

# ── 5. Calcular puntajes (por si el sync/finalizar no lo hizo) ─
print(f"\n== 5) Re-calcular puntajes ==")
try:
    cr = requests.post(f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}",
                       headers=hdr, timeout=300)
    cd = cr.json()
    if cd.get("ok"):
        print(f"   plenos={cd.get('plenos')} aciertos={cd.get('aciertos')} fallos={cd.get('fallos')}")
        for fase, d in (cd.get("por_fase") or {}).items():
            print(f"   [{fase}] marcador={d.get('marcador',0)} bonus={d.get('bonus',0)}"
                  f" total={d.get('total',0)} apuestas={d.get('apuestas',0)}")
        print(f"   globales_procesadas={cd.get('globales_procesadas')}")
    else:
        print(f"   RESPUESTA: {cd}")
except Exception as e:
    print(f"   ERROR: {e}")

# ── 6. Ranking ────────────────────────────────────────────────
print(f"\n== 6) Top 10 Ranking ==")
try:
    rr = requests.get(f"{API_BASE}/bets/ranking/{TORNEO_ID}", headers=hdr, timeout=30)
    data = rr.json()
    # El endpoint puede devolver lista directa o dict con "ranking"
    if isinstance(data, list):
        ranking = data
    elif isinstance(data, dict):
        ranking = data.get("ranking", [])
    else:
        ranking = []
    for i, ap in enumerate(ranking[:10], 1):
        nombre = ap.get('apostador') or ap.get('username') or '?'
        total  = ap.get('puntos_total', 0)
        part   = ap.get('puntos_partidos_total', 0)
        glob_  = ap.get('pts_globales', 0)
        pts_grp = ap.get('pts_grupos_p', 0)
        print(f"  {i:>2}. {nombre:<22} {total:>6} pts"
              f"  (part={part}, glob={glob_}, grp_P={pts_grp})")
except Exception as e:
    print(f"   ERROR ranking: {e}")

# ── 7. Detalle cuartos con puntajes calculados ────────────────
print(f"\n== 7) Detalle puntajes Cuartos (P097-P100) ==")
cur.execute("""
    SELECT p.numero_fifa,
           el.nombre AS local,
           p.goles_local,
           p.goles_visitante,
           ev.nombre AS visitante,
           p.estado,
           COALESCE(ec.nombre, 'sin definir') AS clasificado,
           COUNT(pd.id) AS apostadores_calculados,
           COALESCE(SUM(pd.pts_resultado), 0) AS total_H,
           COALESCE(SUM(pd.pts_marcador), 0)  AS total_I
    FROM partido p
    JOIN equipo el ON el.id = p.equipo_local_id
    JOIN equipo ev ON ev.id = p.equipo_visitante_id
    LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
    LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id
    WHERE p.numero_fifa BETWEEN 97 AND 100
    GROUP BY p.id, p.numero_fifa, el.nombre, p.goles_local, p.goles_visitante,
             ev.nombre, p.estado, ec.nombre
    ORDER BY p.numero_fifa
""")
for r in cur.fetchall():
    print(f"  P{r['numero_fifa']:03d}: {r['local']:<20} {r['goles_local']}-{r['goles_visitante']}"
          f" {r['visitante']:<20} | {r['estado']:<12} | clasifica={r['clasificado']}"
          f" | calc={r['apostadores_calculados']} aposts | H={r['total_H']} I={r['total_I']}")

conn.close()
print("\n✅ Proceso completado.")
