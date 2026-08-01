"""
diag_sync_estado.py
Verifica el estado completo del flujo de sync API-Football → partido:
  1. Configuración: api_league_id, api_season, api_team_id, api_fixture_id
  2. Log de sincronizaciones recientes
  3. Partidos sin datos (amarillas/rojas/var nulos en finalizados)
  4. Prueba directa de un call a API-Football
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import psycopg2
import os, sys

DB = {"host": "localhost", "port": 5432,
      "dbname": "becbuc", "user": "app_user", "password": "app_password"}

def conectar():
    try:
        return psycopg2.connect(**DB)
    except Exception:
        d = {k: v for k, v in DB.items() if k != "password"}
        return psycopg2.connect(**d)

def main():
    conn = conectar()
    cur  = conn.cursor()

    print("\n" + "="*65)
    print("DIAGNÓSTICO SYNC API-FOOTBALL → PARTIDOS")
    print("="*65)

    # ── 1. Configuración torneo ───────────────────────────────────────────
    print("\n── 1. CONFIGURACIÓN TORNEO ──────────────────────────────────────")
    cur.execute("""
        SELECT t.id, t.nombre, t.api_season,
               c.nombre AS competicion, c.api_league_id
        FROM torneo t
        JOIN competicion c ON c.id = t.competicion_id
        WHERE t.id = 2
    """)
    row = cur.fetchone()
    if row:
        print(f"  Torneo:       {row[1]} (id={row[0]})")
        print(f"  Competicion:  {row[3]}")
        print(f"  api_league_id: {row[4]}  {'✅' if row[4] else '❌ FALTA'}")
        print(f"  api_season:    {row[2]}  {'✅' if row[2] else '❌ FALTA'}")
    else:
        print("  ❌ Torneo id=2 no encontrado")

    # ── 2. Mapeo equipos ──────────────────────────────────────────────────
    print("\n── 2. MAPEO EQUIPOS (api_team_id) ───────────────────────────────")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE api_team_id IS NOT NULL) AS mapeados,
            COUNT(*) AS total
        FROM equipo
    """)
    m, t = cur.fetchone()
    pct = 100*m/t if t else 0
    print(f"  Equipos mapeados: {m}/{t} ({pct:.0f}%) {'✅' if pct==100 else '⚠️'}")

    # ── 3. Mapeo fixtures ──────────────────────────────────────────────────
    print("\n── 3. MAPEO PARTIDOS (api_fixture_id) ───────────────────────────")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE api_fixture_id IS NOT NULL) AS mapeados,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE api_fixture_id IS NULL AND estado != 'pendiente') AS sin_mapeo_activos
        FROM partido
        WHERE torneo_id = 2
    """)
    m, t, act = cur.fetchone()
    pct = 100*m/t if t else 0
    print(f"  Partidos mapeados: {m}/{t} ({pct:.0f}%) {'✅' if pct==100 else '⚠️'}")
    if act:
        print(f"  ⚠️  {act} partidos no-pendientes sin api_fixture_id (no se sincronizarán en detalle)")

    # ── 4. Partidos finalizados con datos incompletos ─────────────────────
    print("\n── 4. PARTIDOS FINALIZADOS CON DATOS INCOMPLETOS ────────────────")
    cur.execute("""
        SELECT p.numero_fifa,
               COALESCE(el.nombre_es, el.nombre) as local,
               COALESCE(ev.nombre_es, ev.nombre) as visitante,
               p.amarillas, p.rojas, p.decisiones_var,
               p.api_fixture_id
        FROM partido p
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.torneo_id = 2
          AND p.estado = 'finalizado'
          AND (p.amarillas IS NULL OR p.rojas IS NULL OR p.decisiones_var IS NULL)
        ORDER BY p.numero_fifa
    """)
    rows = cur.fetchall()
    if rows:
        print(f"  {len(rows)} partido(s) finalizados con campos nulos:")
        print(f"  {'P#':<4} {'Partido':<35} {'Amar':>5} {'Rojas':>6} {'VAR':>5} {'fixture_id':>12}")
        print(f"  {'─'*70}")
        for r in rows:
            print(f"  P{str(r[0]):<3} {str(r[1])+' vs '+str(r[2]):<35} "
                  f"{str(r[3] or 'NULL'):>5} {str(r[4] or 'NULL'):>6} "
                  f"{str(r[5] or 'NULL'):>5} {str(r[6] or 'NULL'):>12}")
    else:
        print("  ✅ Todos los partidos finalizados tienen amarillas/rojas/VAR")

    # ── 5. Últimas sincronizaciones ───────────────────────────────────────
    print("\n── 5. ÚLTIMAS SINCRONIZACIONES (api_sync_log) ───────────────────")
    try:
        cur.execute("""
            SELECT created_at, contexto, ok, error_msg, calls_used
            FROM api_sync_log
            ORDER BY created_at DESC
            LIMIT 10
        """)
        logs = cur.fetchall()
        if logs:
            print(f"  {'Fecha':<22} {'Contexto':<25} {'OK':>4} {'Calls':>6}  Detalle")
            print(f"  {'─'*75}")
            for lg in logs:
                ts  = str(lg[0])[:19] if lg[0] else '?'
                ctx = (lg[1] or '')[:24]
                ok  = '✅' if lg[2] else '❌'
                calls = lg[4] or 0
                err = (lg[3] or '')[:30]
                print(f"  {ts:<22} {ctx:<25} {ok:>4} {calls:>6}  {err}")
        else:
            print("  (sin registros en api_sync_log)")
    except Exception as e:
        print(f"  ⚠️  No se pudo leer api_sync_log: {e}")

    # ── 6. API key ────────────────────────────────────────────────────────
    print("\n── 6. API KEY API-FOOTBALL ──────────────────────────────────────")
    # Intentar leer desde el backend config
    sys.path.insert(0, _osp.path.join(_BASE, 'backend'))
    try:
        from app.core.config import settings
        key = getattr(settings, "API_FOOTBALL_KEY", None) or \
              getattr(settings, "RAPIDAPI_KEY", None)
        if key:
            print(f"  ✅ API key configurada: {key[:8]}...{key[-4:]}")
        else:
            print("  ❌ API key NO encontrada en settings")
            # Buscar en variables de entorno
            env_key = os.getenv("API_FOOTBALL_KEY") or os.getenv("RAPIDAPI_KEY")
            if env_key:
                print(f"  ✅ Encontrada en env: {env_key[:8]}...")
            else:
                print("  ❌ Tampoco en variables de entorno")
    except Exception as e:
        print(f"  ⚠️  No se pudo importar settings: {e}")
        env_key = os.getenv("API_FOOTBALL_KEY") or os.getenv("RAPIDAPI_KEY")
        if env_key:
            print(f"  ✅ Env var API_FOOTBALL_KEY: {env_key[:8]}...")
        else:
            print("  ❌ Sin API key en entorno")

    # ── 7. Resumen y recomendaciones ──────────────────────────────────────
    print("\n── 7. RESUMEN ───────────────────────────────────────────────────")
    cur.execute("SELECT COUNT(*) FROM partido WHERE torneo_id=2 AND api_fixture_id IS NULL")
    sin_fixture = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM equipo WHERE api_team_id IS NULL")
    sin_team = cur.fetchone()[0]

    if sin_fixture > 0:
        print(f"  ⚠️  {sin_fixture} partidos sin api_fixture_id → ejecutar auto-mapeo:")
        print(f"       POST /api/v1/bets/api-mapeo/2/auto")
    if sin_team > 0:
        print(f"  ⚠️  {sin_team} equipos sin api_team_id → mapeo de equipos incompleto")
    if sin_fixture == 0 and sin_team == 0:
        print(f"  ✅ Mapeo completo — sync detallado disponible para todos los partidos")
    print()

    conn.close()

if __name__ == "__main__":
    main()
