"""
diag_espn_matching.py
Diagnóstico del matching ESPN con el nuevo mapa ES→EN.
Ahora SofaScore está deshabilitado (403), solo probamos ESPN.
"""
import asyncio
import httpx
import psycopg2
import unicodedata
import re

SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
SOFASCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}

DB = {"host": "localhost", "port": 5432,
      "dbname": "becbuc", "user": "app_user", "password": "app_password"}

def _normalize(name: str) -> str:
    if not name:
        return ""
    n = unicodedata.normalize("NFD", name.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    n = re.sub(r"[^\w\s]", " ", n)
    n = re.sub(r"\b(fc|cf|sc|ac|bv|sv|vv|de|del|la|el|los|las|the|united|city|club|team)\b", "", n)
    return " ".join(n.split())

def get_fechas():
    try:
        conn = psycopg2.connect(**DB)
    except Exception:
        d = {k: v for k, v in DB.items() if k != "password"}
        conn = psycopg2.connect(**d)
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT DATE(p.fecha) as d,
               COALESCE(el.nombre_es, el.nombre) as local,
               COALESCE(ev.nombre_es, ev.nombre) as visitante
        FROM partido p
        LEFT JOIN equipo el ON el.id = p.equipo_local_id
        LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
        WHERE p.estado = 'finalizado'
          AND p.torneo_id = 2
        ORDER BY d
        LIMIT 5
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

async def test_sofascore():
    fechas = get_fechas()
    if not fechas:
        print("No hay partidos finalizados en BD")
        return

    async with httpx.AsyncClient() as client:
        for fecha_row in fechas[:3]:  # solo primeras 3 fechas
            fecha_str = str(fecha_row[0])
            local_bd  = fecha_row[1]
            visit_bd  = fecha_row[2]

            print(f"\n{'='*60}")
            print(f"Fecha: {fecha_str}")
            print(f"BD: {local_bd} vs {visit_bd}")

            url = f"{SOFASCORE_BASE}/sport/football/scheduled-events/{fecha_str}"
            try:
                r = await client.get(url, headers=SOFASCORE_HEADERS, timeout=15)
                print(f"HTTP status: {r.status_code}")

                if r.status_code != 200:
                    print(f"Respuesta: {r.text[:200]}")
                    continue

                data = r.json()
                events = data.get("events", [])
                print(f"Total eventos del día: {len(events)}")

                # Filtrar solo fútbol internacional (tournament category)
                print(f"\nPrimeros 5 partidos devueltos por SofaScore:")
                for ev in events[:5]:
                    home = ev.get("homeTeam", {}).get("name", "?")
                    away = ev.get("awayTeam", {}).get("name", "?")
                    tour = ev.get("tournament", {}).get("name", "?")
                    status = ev.get("status", {}).get("type", "?")
                    print(f"  [{ev.get('id')}] {home} vs {away}  ({tour}) [{status}]")

                # Buscar Copa del Mundo específicamente
                mundial = [ev for ev in events
                           if "world" in ev.get("tournament", {}).get("name", "").lower()
                           or "copa" in ev.get("tournament", {}).get("name", "").lower()
                           or "fifa" in str(ev.get("tournament", {})).lower()
                           or ev.get("tournament", {}).get("uniqueTournament", {}).get("id") in [6, 7, 8, 9, 16, 17]]
                print(f"\nPartidos Copa del Mundo encontrados: {len(mundial)}")
                for ev in mundial:
                    home = ev.get("homeTeam", {}).get("name", "?")
                    away = ev.get("awayTeam", {}).get("name", "?")
                    tour = ev.get("tournament", {}).get("name", "?")
                    tid  = ev.get("tournament", {}).get("uniqueTournament", {}).get("id", "?")
                    print(f"  [{ev.get('id')}] {home} vs {away}  (tour={tour}, tid={tid})")

                # Test matching con nombres de BD
                print(f"\nTest matching '{local_bd}' vs '{visit_bd}':")
                loc_n = _normalize(local_bd)
                vis_n = _normalize(visit_bd)
                print(f"  Normalizado BD: '{loc_n}' vs '{vis_n}'")
                found = False
                for ev in events:
                    home = ev.get("homeTeam", {}).get("name", "")
                    away = ev.get("awayTeam", {}).get("name", "")
                    home_n = _normalize(home)
                    away_n = _normalize(away)
                    match_dir = ((loc_n in home_n or home_n in loc_n) and
                                 (vis_n in away_n or away_n in vis_n))
                    match_inv = ((vis_n in home_n or home_n in vis_n) and
                                 (loc_n in away_n or away_n in loc_n))
                    if match_dir or match_inv:
                        print(f"  ✅ MATCH: {home} vs {away} (event_id={ev.get('id')})")
                        found = True
                        break
                if not found:
                    print(f"  ❌ Sin match — mostrando candidatos con nombres similares:")
                    for ev in events[:20]:
                        home = ev.get("homeTeam", {}).get("name", "")
                        away = ev.get("awayTeam", {}).get("name", "")
                        home_n = _normalize(home)
                        away_n = _normalize(away)
                        # Ver si hay algo parecido
                        if any(w in home_n or w in away_n
                               for w in loc_n.split() + vis_n.split() if len(w) > 3):
                            print(f"    Candidato: [{_normalize(home)}] vs [{_normalize(away)}]  (raw: {home} vs {away})")

            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

    print("\n\nDIAGNÓSTICO COMPLETO")

if __name__ == "__main__":
    asyncio.run(test_sofascore())
