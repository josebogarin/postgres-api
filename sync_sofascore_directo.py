"""
sync_sofascore_directo.py — Corrige J/K/L/M de partidos recientes usando SofaScore.
NO requiere uvicorn corriendo. Conecta directo a PostgreSQL y llama SofaScore API.

Uso:
    python sync_sofascore_directo.py           # partidos de ayer
    python sync_sofascore_directo.py hoy       # partidos de hoy
    python sync_sofascore_directo.py 2026-06-24  # fecha especifica
    python sync_sofascore_directo.py force       # todos los partidos finalizados
"""
import sys
import json
import unicodedata
import re
import urllib.request
import urllib.error
from datetime import date, timedelta, datetime

# ── Dependencias ──────────────────────────────────────────────────────────────
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 no instalado.")
    print("Instalar: backend\\.venv\\Scripts\\pip install psycopg2-binary")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
DB_DSN = "host=localhost port=5432 dbname=becbuc user=app_user password=app_password"
TORNEO_ID = 2

SOFASCORE_BASE = "https://api.sofascore.com/api/v1"
SOFASCORE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
}

# ── Normalización ─────────────────────────────────────────────────────────────
def _normalize(name: str) -> str:
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^\w\s]", " ", name.lower())
    for word in ("fc","cf","afc","sc","ac","de","del","la","el","los","las","the","team","national","republic"):
        name = re.sub(rf"\b{word}\b", "", name)
    return re.sub(r"\s+", " ", name).strip()

# ── HTTP helper ───────────────────────────────────────────────────────────────
def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=SOFASCORE_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"    HTTP {e.code}: {url}")
        return {}
    except Exception as e:
        print(f"    Error: {e} ({url})")
        return {}

# ── SofaScore helpers ─────────────────────────────────────────────────────────
def ss_get_events(fecha_str: str) -> list:
    data = _get(f"{SOFASCORE_BASE}/sport/football/scheduled-events/{fecha_str}")
    return data.get("events", [])

def ss_find_event(events: list, local: str, visitante: str) -> int | None:
    loc_n = _normalize(local)
    vis_n = _normalize(visitante)
    for ev in events:
        home = _normalize(ev.get("homeTeam", {}).get("name", ""))
        away = _normalize(ev.get("awayTeam", {}).get("name", ""))
        match_dir = (any(loc_n in h or h in loc_n for h in [home] if h) and
                     any(vis_n in a or a in vis_n for a in [away] if a))
        match_inv = (any(vis_n in h or h in vis_n for h in [home] if h) and
                     any(loc_n in a or a in loc_n for a in [away] if a))
        if loc_n and vis_n and (match_dir or match_inv):
            return ev.get("id")
    return None

def ss_get_incidents(event_id: int) -> list:
    data = _get(f"{SOFASCORE_BASE}/event/{event_id}/incidents")
    return data.get("incidents", [])

def ss_extract_stats(incidents: list) -> dict:
    amarillas = 0
    rojas = 0
    decisiones_var = 0
    penales_partido = 0
    _SHOOTOUT = {5, "5", "penalties"}
    for inc in incidents:
        inc_type  = inc.get("incidentType", "")
        inc_class = inc.get("incidentClass", "")
        period    = inc.get("period", {})
        pval      = period.get("value") if isinstance(period, dict) else period
        if pval in _SHOOTOUT:
            continue
        if inc_type == "card":
            if inc_class == "yellow":
                amarillas += 1
            elif inc_class in ("yellowRed", "red"):
                rojas += 1
        elif inc_type == "varDecision":
            decisiones_var += 1
        elif inc_type == "goal" and inc_class == "penalty":
            penales_partido += 1
        elif inc_type == "missedPenalty":
            penales_partido += 1
    return {"amarillas": amarillas, "rojas": rojas,
            "decisiones_var": decisiones_var, "penales_partido": penales_partido}

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "ayer"

    if arg == "hoy":
        fechas = [date.today()]
        label  = "hoy"
    elif arg == "force":
        fechas = None   # todos los finalizados
        label  = "todos los finalizados"
    elif arg == "ayer":
        fechas = [date.today() - timedelta(days=1)]
        label  = "ayer"
    else:
        try:
            fechas = [datetime.strptime(arg, "%Y-%m-%d").date()]
            label  = arg
        except ValueError:
            print(f"Argumento no reconocido: {arg}")
            print("Uso: python sync_sofascore_directo.py [ayer|hoy|force|YYYY-MM-DD]")
            sys.exit(1)

    print("=" * 60)
    print(f"  SYNC SOFASCORE DIRECTO — {label.upper()}")
    print("=" * 60)

    try:
        conn = psycopg2.connect(DB_DSN)
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except Exception as e:
        print(f"ERROR conectando a PostgreSQL: {e}")
        print("Verificá que el Docker core-postgres esté corriendo.")
        sys.exit(1)

    print("✓ Conectado a PostgreSQL")

    # ── Cargar partidos ───────────────────────────────────────────────────────
    if fechas is None:
        cur.execute("""
            SELECT p.id, p.fecha,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre,
                   p.amarillas, p.rojas, p.decisiones_var, p.penales_partido
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE f.torneo_id = %s AND p.estado = 'finalizado'
            ORDER BY p.fecha DESC
        """, (TORNEO_ID,))
    else:
        placeholders = ",".join(["%s"] * len(fechas))
        cur.execute(f"""
            SELECT p.id, p.fecha,
                   COALESCE(el.nombre_es, el.nombre) AS local_nombre,
                   COALESCE(ev.nombre_es, ev.nombre) AS visit_nombre,
                   p.amarillas, p.rojas, p.decisiones_var, p.penales_partido
            FROM partido p
            JOIN fase f ON f.id = p.fase_id
            JOIN equipo el ON el.id = p.equipo_local_id
            JOIN equipo ev ON ev.id = p.equipo_visitante_id
            WHERE f.torneo_id = %s AND p.estado = 'finalizado'
              AND DATE(p.fecha) IN ({placeholders})
            ORDER BY p.fecha
        """, [TORNEO_ID] + list(fechas))

    partidos = cur.fetchall()
    print(f"Partidos finalizados encontrados: {len(partidos)}")
    if not partidos:
        print("Nada que sincronizar.")
        conn.close()
        return

    # ── Cache de eventos SofaScore por fecha ─────────────────────────────────
    ss_cache: dict[str, list] = {}
    correcciones = []
    sin_match    = []

    for p in partidos:
        local     = p["local_nombre"]
        visitante = p["visit_nombre"]
        fecha_p   = p["fecha"]
        fecha_str = fecha_p.strftime("%Y-%m-%d") if hasattr(fecha_p, "strftime") else str(fecha_p)[:10]

        print(f"\n  [{fecha_str}] {local} vs {visitante}")

        # Cargar eventos SofaScore del día (caché)
        if fecha_str not in ss_cache:
            print(f"    Cargando eventos SofaScore {fecha_str}...")
            ss_cache[fecha_str] = ss_get_events(fecha_str)
            print(f"    {len(ss_cache[fecha_str])} eventos encontrados")

        events = ss_cache[fecha_str]
        event_id = ss_find_event(events, local, visitante)
        if not event_id:
            print(f"    ⚠ No encontrado en SofaScore")
            sin_match.append(f"{local} vs {visitante}")
            continue

        print(f"    ✓ SofaScore event_id={event_id}")
        incidents = ss_get_incidents(event_id)
        if not incidents:
            print(f"    ⚠ Sin incidents")
            continue

        ss = ss_extract_stats(incidents)
        print(f"    Stats SS → J:{ss['amarillas']} K:{ss['rojas']} L:{ss['decisiones_var']} M:{ss['penales_partido']}")
        print(f"    Stats BD → J:{p['amarillas'] or 0} K:{p['rojas'] or 0} L:{p['decisiones_var'] or 0} M:{p['penales_partido'] or 0}")

        updates = {}
        if ss["amarillas"]       != (p["amarillas"]       or 0): updates["amarillas"]       = ss["amarillas"]
        if ss["rojas"]           != (p["rojas"]           or 0): updates["rojas"]           = ss["rojas"]
        if ss["decisiones_var"]  != (p["decisiones_var"]  or 0): updates["decisiones_var"]  = ss["decisiones_var"]
        if ss["penales_partido"] != (p["penales_partido"] or 0): updates["penales_partido"] = ss["penales_partido"]

        if not updates:
            print(f"    ✓ Sin diferencias")
            continue

        print(f"    🔧 Corrigiendo: {updates}")
        set_clause = ", ".join(f"{k} = %s" for k in updates)
        cur.execute(
            f"UPDATE partido SET {set_clause} WHERE id = %s",
            list(updates.values()) + [p["id"]]
        )
        correcciones.append({"partido_id": p["id"], "local": local, "visitante": visitante, "updates": updates})

    # ── Commit ────────────────────────────────────────────────────────────────
    if correcciones:
        conn.commit()
        print(f"\n✓ {len(correcciones)} partido(s) corregidos en BD")
    else:
        print(f"\n✓ Sin correcciones necesarias")

    if sin_match:
        print(f"⚠ {len(sin_match)} partido(s) no encontrados en SofaScore:")
        for s in sin_match:
            print(f"   - {s}")

    cur.close()
    conn.close()

    # ── Recalcular puntajes ───────────────────────────────────────────────────
    if correcciones:
        print("\nRecalculando puntajes via API...")
        try:
            import urllib.parse
            token_payload = urllib.parse.urlencode({"username": "jose", "password": "catalina"}).encode()
            req = urllib.request.Request(
                "http://localhost:8000/api/v1/auth/login",
                data=token_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as r:
                token = json.loads(r.read())["access_token"]
            req2 = urllib.request.Request(
                f"http://localhost:8000/api/v1/bets/calcular-puntajes/{TORNEO_ID}",
                data=b"",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req2, timeout=60) as r2:
                pts = json.loads(r2.read())
            print(f"  Plenos: {pts.get('plenos','?')} | Aciertos: {pts.get('aciertos','?')}")
        except Exception as e:
            print(f"  (servidor no disponible: {e})")
            print("  Recalcular manualmente cuando el servidor esté activo.")

    print("\nListo.")

if __name__ == "__main__":
    main()
