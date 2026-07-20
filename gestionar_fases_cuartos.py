# -*- coding: utf-8 -*-
"""
gestionar_fases_cuartos.py
1) Muestra estado actual de fases
2) Bloquea Octavos (ronda16) si no estaba bloqueada
3) Desbloquea Cuartos para que el engine pueda calcular
4) POST /calcular-puntajes/2
5) Muestra ranking top-10 actualizado
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

print("=" * 60)
print("BECBUC - Gestionar fases: Cerrar Octavos / Abrir Cuartos")
print("=" * 60)

# ── Conectar BD ───────────────────────────────────────────────
try:
    conn = psycopg2.connect(CONN_BEC)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
except Exception as e:
    sys.exit(f"ERROR conexion BD: {e}")

# ── 1. Ver estado actual de fases ─────────────────────────────
print("\n== 1) Estado actual de fases ==")
cur.execute("""
    SELECT f.id, f.nombre, f.tipo,
           COALESCE(f.bloqueada, FALSE) AS bloqueada,
           COUNT(p.id) AS total,
           COUNT(CASE WHEN p.estado='finalizado' THEN 1 END) AS finalizados
    FROM fase f
    LEFT JOIN partido p ON p.fase_id = f.id
    WHERE f.torneo_id = %s
    GROUP BY f.id, f.nombre, f.tipo, f.bloqueada
    ORDER BY f.id
""", (TORNEO_ID,))
todas_fases = cur.fetchall()

for f in todas_fases:
    flag = "[BLOQ]" if f['bloqueada'] else "[ABIE]"
    print(f"  {flag} id={f['id']:>3} tipo={f['tipo']:<20} '{f['nombre']}' "
          f"({f['finalizados']}/{f['total']} fin.)")

# ── 2. Bloquear Octavos (ronda16) ────────────────────────────
print("\n== 2) Cerrando Octavos (ronda16) ==")
oct_fases = [f for f in todas_fases
             if 'ronda16' in (f['tipo'] or '').lower()
             or '16avos' in (f['tipo'] or '').lower()
             or 'octavo' in (f['nombre'] or '').lower()]

if not oct_fases:
    print("  ⚠  No se encontro fase ronda16/octavos. Fases disponibles:")
    for f in todas_fases:
        print(f"     id={f['id']} tipo='{f['tipo']}' nombre='{f['nombre']}'")
else:
    for f in oct_fases:
        if f['bloqueada']:
            print(f"  ✓  id={f['id']} '{f['nombre']}' ya estaba BLOQUEADA")
        else:
            cur.execute("UPDATE fase SET bloqueada=TRUE WHERE id=%s", (f['id'],))
            print(f"  ✅ id={f['id']} '{f['nombre']}' -> BLOQUEADA ahora")

# ── 3. Desbloquear Cuartos ────────────────────────────────────
print("\n== 3) Abriendo Cuartos para calculo ==")
cua_fases = [f for f in todas_fases
             if 'cuarto' in (f['tipo'] or '').lower()
             or 'cuarto' in (f['nombre'] or '').lower()]

if not cua_fases:
    print("  ⚠  No se encontro fase cuartos. Fases disponibles arriba.")
else:
    for f in cua_fases:
        cur.execute("UPDATE fase SET bloqueada=FALSE WHERE id=%s", (f['id'],))
        estado_ant = "BLOQUEADA" if f['bloqueada'] else "ya abierta"
        print(f"  ✅ id={f['id']} '{f['nombre']}' -> DESBLOQUEADA (antes: {estado_ant})")

# ── Mostrar partidos de Cuartos ───────────────────────────────
if cua_fases:
    ids_cuartos = [f['id'] for f in cua_fases]
    cur.execute("""
        SELECT p.numero_fifa,
               el.nombre  AS local,
               p.goles_local,
               p.goles_visitante,
               ev.nombre  AS visitante,
               p.estado,
               COALESCE(ec.nombre, 'sin definir') AS clasificado,
               COALESCE(p.datos_confirmados, FALSE) AS confirmado
        FROM partido p
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        LEFT JOIN equipo ec ON ec.id = p.equipo_clasificado_id
        WHERE p.fase_id = ANY(%s)
        ORDER BY p.numero_fifa
    """, (ids_cuartos,))
    partidos = cur.fetchall()
    print("\n   Partidos de Cuartos:")
    for p in partidos:
        conf = " [CONFIRMADO]" if p['confirmado'] else ""
        print(f"   P{p['numero_fifa']:03d}: {p['local']:<25} {p['goles_local']}-"
              f"{p['goles_visitante']} {p['visitante']:<25} | {p['estado']:<12}"
              f" | Clasifica: {p['clasificado']}{conf}")

conn.close()

# ── 4. Calcular puntajes via API ─────────────────────────────
print("\n== 4) Calculando puntajes (POST /calcular-puntajes/2) ==")
try:
    lr = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": API_USER, "password": API_PASS},
        timeout=30
    )
    tok = lr.json().get("access_token", "")
except Exception as e:
    sys.exit(f"ERROR login (uvicorn corriendo en :8000?): {e}")

if not tok:
    sys.exit(f"ERROR: login sin token -> {lr.status_code} {lr.text[:200]}")

hdr = {"Authorization": f"Bearer {tok}"}

try:
    cr = requests.post(
        f"{API_BASE}/bets/calcular-puntajes/{TORNEO_ID}",
        headers=hdr,
        timeout=300
    )
    cd = cr.json()
except Exception as e:
    sys.exit(f"ERROR recalculo: {e}")

if cd.get("ok"):
    print(f"  plenos={cd.get('plenos')}  aciertos={cd.get('aciertos')}  fallos={cd.get('fallos')}")
    for fase, d in (cd.get("por_fase") or {}).items():
        print(f"    [{fase}] marcador={d.get('marcador',0)}  bonus={d.get('bonus',0)}"
              f"  total={d.get('total',0)}  apuestas={d.get('apuestas',0)}")
    print(f"  globales_procesadas={cd.get('globales_procesadas')}")
else:
    print(f"  RESPUESTA: {cd}")

# ── 5. Ranking top-10 ─────────────────────────────────────────
print("\n== 5) Top 10 Ranking ==")
try:
    rr = requests.get(f"{API_BASE}/bets/ranking/{TORNEO_ID}", headers=hdr, timeout=30)
    ranking = rr.json().get("ranking", [])
    for i, ap in enumerate(ranking[:10], 1):
        nombre = ap.get('apostador') or ap.get('username') or '?'
        total  = ap.get('puntos_total', 0)
        part   = ap.get('puntos_partidos_total', 0)
        glob_  = ap.get('pts_globales', 0)
        print(f"  {i:>2}. {nombre:<20} {total:>6} pts  (partidos={part}, globales={glob_})")
except Exception as e:
    print(f"  Error ranking: {e}")

print("\n✅ Proceso completado.")
