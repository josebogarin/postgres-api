"""
cargar_goleadores.py
Limpia y recarga la tabla goleadores_cache desde API-Football.

Uso:
  python cargar_goleadores.py                  # usa COMPETICION_ID=2 por defecto
  python cargar_goleadores.py --competencia 2  # mismo resultado
  python cargar_goleadores.py --torneo 2       # busca por torneo_id directamente
"""
import asyncio
import argparse
import httpx
import psycopg2

# ── Config ──────────────────────────────────────────────────────────────────
APIFOOTBALL_KEY  = "f13bee776659e2c20c715a81ecff2307"
BECBUC_DB        = "postgresql://app_user:superpassword@localhost:5432/becbuc"

DEFAULT_COMPETICION_ID = 2     # Copa del Mundo 2026
API_LEAGUE_ID    = 1           # FIFA World Cup en API-Football (fallback)
API_SEASON       = 2026        # fallback si t.api_season es NULL

# ── BD ──────────────────────────────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(BECBUC_DB)

def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS goleadores_cache (
                id SERIAL PRIMARY KEY,
                torneo_id       INTEGER NOT NULL,
                jugador_id      INTEGER NOT NULL,
                nombre          VARCHAR(200) NOT NULL,
                foto_url        VARCHAR(500),
                equipo_nombre   VARCHAR(200),
                equipo_logo     VARCHAR(500),
                goles           INTEGER DEFAULT 0,
                asistencias     INTEGER DEFAULT 0,
                posicion        INTEGER DEFAULT 1,
                actualizado_at  TIMESTAMP DEFAULT NOW(),
                UNIQUE (torneo_id, jugador_id)
            )
        """)
    conn.commit()

def get_torneo_info(conn, torneo_id=None, competicion_id=None):
    """
    Retorna (torneo_id, api_season, api_league_id, nombre_competicion).
    Busca por torneo_id si se provee, sino por competicion_id (último torneo).
    """
    with conn.cursor() as cur:
        if torneo_id:
            cur.execute("""
                SELECT t.id,
                       COALESCE(t.api_season, %s),
                       COALESCE(c.api_league_id, %s),
                       c.nombre
                FROM torneo t
                JOIN competicion c ON c.id = t.competicion_id
                WHERE t.id = %s
            """, (API_SEASON, API_LEAGUE_ID, torneo_id))
        else:
            cur.execute("""
                SELECT t.id,
                       COALESCE(t.api_season, %s),
                       COALESCE(c.api_league_id, %s),
                       c.nombre
                FROM torneo t
                JOIN competicion c ON c.id = t.competicion_id
                WHERE c.id = %s
                ORDER BY t.id DESC
                LIMIT 1
            """, (API_SEASON, API_LEAGUE_ID, competicion_id))
        row = cur.fetchone()

    if not row:
        crit = f"torneo_id={torneo_id}" if torneo_id else f"competicion_id={competicion_id}"
        print(f"  ⚠ No se encontró torneo con {crit}. Usando defaults.")
        return (torneo_id or competicion_id or 2), API_SEASON, API_LEAGUE_ID, "Torneo desconocido"
    return row[0], row[1], row[2], row[3]

def delete_existing(conn, torneo_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM goleadores_cache WHERE torneo_id = %s", (torneo_id,))
        deleted = cur.rowcount
    conn.commit()
    print(f"  {deleted} registros anteriores eliminados.")

# ── API-Football ─────────────────────────────────────────────────────────────
async def fetch_top_scorers(league_id, season):
    print(f"  GET topscorers · league={league_id} season={season} …")
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://v3.football.api-sports.io/players/topscorers",
            params={"league": league_id, "season": season},
            headers={"x-apisports-key": APIFOOTBALL_KEY},
        )
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    data      = resp.json()
    errors    = data.get("errors", [])
    remaining = resp.headers.get("x-ratelimit-requests-remaining", "?")
    print(f"  Cuota restante: {remaining}")
    if errors:
        raise RuntimeError(f"API errors: {errors}")
    return data.get("response", [])

# ── Insertar ─────────────────────────────────────────────────────────────────
def insert_scorers(conn, torneo_id, scorers):
    with conn.cursor() as cur:
        for i, item in enumerate(scorers[:20]):
            p     = item.get("player", {})
            s     = (item.get("statistics") or [{}])[0]
            goles  = (s.get("goals") or {}).get("total") or 0
            asist  = (s.get("goals") or {}).get("assists") or 0
            equipo = (s.get("team") or {}).get("name") or ""
            logo   = (s.get("team") or {}).get("logo") or ""
            cur.execute("""
                INSERT INTO goleadores_cache
                    (torneo_id, jugador_id, nombre, foto_url,
                     equipo_nombre, equipo_logo, goles, asistencias, posicion, actualizado_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (torneo_id, jugador_id) DO UPDATE SET
                    nombre         = EXCLUDED.nombre,
                    foto_url       = EXCLUDED.foto_url,
                    equipo_nombre  = EXCLUDED.equipo_nombre,
                    equipo_logo    = EXCLUDED.equipo_logo,
                    goles          = EXCLUDED.goles,
                    asistencias    = EXCLUDED.asistencias,
                    posicion       = EXCLUDED.posicion,
                    actualizado_at = NOW()
            """, (
                torneo_id,
                p.get("id") or (i + 1),
                p.get("name") or "?",
                p.get("photo") or "",
                equipo,
                logo,
                goles,
                asist,
                i + 1,
            ))
            print(f"  {i+1:2d}. {p.get('name','?'):<28s} {goles}⚽  {equipo}")
    conn.commit()

# ── Main ─────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Recargar goleadores en goleadores_cache")
    parser.add_argument("--competencia", type=int, default=None,
                        help=f"competicion_id (default={DEFAULT_COMPETICION_ID})")
    parser.add_argument("--torneo", type=int, default=None,
                        help="torneo_id directo (tiene prioridad sobre --competencia)")
    args = parser.parse_args()

    torneo_arg     = args.torneo
    competencia_id = args.competencia or DEFAULT_COMPETICION_ID

    print("=" * 60)
    print("BECBUC — Recargar goleadores (delete + insert)")
    print("=" * 60)

    conn = get_conn()
    try:
        print(f"\n1. Preparando tabla…")
        ensure_table(conn)

        print("\n2. Buscando torneo…")
        torneo_id, season, league_id, nombre = get_torneo_info(
            conn, torneo_id=torneo_arg, competicion_id=competencia_id
        )
        print(f"   {nombre}  ·  torneo_id={torneo_id}  league={league_id}  season={season}")

        print("\n3. Eliminando registros existentes…")
        delete_existing(conn, torneo_id)

        print("\n4. Consultando API-Football…")
        scorers = await fetch_top_scorers(league_id, season)

        if not scorers:
            print("\n⚠ La API devolvió 0 jugadores.")
            print("  Posibles causas: cuota agotada, league/season incorrectos, torneo no iniciado.")
            return

        print(f"\n5. Insertando top {min(len(scorers), 20)}:\n")
        insert_scorers(conn, torneo_id, scorers)

        print(f"\n✅ {min(len(scorers), 20)} goleadores cargados (torneo_id={torneo_id}).")
        print("   Recargá el dashboard o monitoreo/globales para verlos.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(main())
