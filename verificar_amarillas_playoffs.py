"""
verificar_amarillas_playoffs.py
================================
Verifica el conteo de tarjetas amarillas en partidos de playoffs (Copa del Mundo 2026)
consultando API-Football directamente y comparando con lo que hay en la BD BECBUC.

Lógica de conteo (idéntica a sync_api_football.py):
  - PRIMARIO: eventos type=="Card" AND detail=="Yellow Card" AND player.id != None
              (excluye "Second Yellow card" que es expulsión → se cuenta como roja)
  - FALLBACK: si no hay eventos, usa estadísticas "Yellow Cards" de API-Football

Uso:
  python verificar_amarillas_playoffs.py           -- solo reporta diferencias
  python verificar_amarillas_playoffs.py --apply   -- reporta Y actualiza BD

Requiere:
  pip install psycopg2-binary requests
  .env en C:\\proyecto FAST API\\backend\\.env con APIFOOTBALL_KEY
"""

import sys
import os
import json
import time
import requests
import psycopg2
from datetime import datetime

# ── Configuración ──────────────────────────────────────────────────────────────

DB_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "user": "app_user",
    "password": "superpassword",
    "dbname": "becbuc",
}

APIFOOTBALL_KEY = "f13bee776659e2c20c715a81ecff2307"
API_BASE = "https://v3.football.api-sports.io"

APPLY = "--apply" in sys.argv
DRY_RUN = not APPLY

# ── Helpers ────────────────────────────────────────────────────────────────────

def api_headers():
    return {
        "x-rapidapi-key": APIFOOTBALL_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


def fetch_fixture(fixture_id: int) -> dict | None:
    """Llama GET /fixtures?id={fixture_id} y retorna el primer resultado."""
    url = f"{API_BASE}/fixtures"
    params = {"id": fixture_id}
    try:
        r = requests.get(url, headers=api_headers(), params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        remaining = int(r.headers.get("x-ratelimit-requests-remaining", -1))
        results = data.get("response", [])
        return results[0] if results else None, remaining
    except Exception as e:
        print(f"  ERROR API: {e}")
        return None, -1


def parse_yellow_cards(fix: dict) -> dict:
    """
    Parsea el fixture de API-Football y extrae:
      amarillas_events  -- conteo por eventos (fuente primaria, más precisa)
      amarillas_stats   -- conteo por estadísticas (fallback)
      amarillas_final   -- el valor que se usaría en BD
      rojas             -- rojas del partido
      eventos_count     -- total eventos del fixture
    """
    events = fix.get("events", []) or []
    events_sorted = sorted(events, key=lambda e: (e.get("time") or {}).get("elapsed") or 999)

    amarillas_ev = 0
    rojas_ev = 0

    for ev in events_sorted:
        t = ev.get("type", "")
        d = ev.get("detail", "")
        pid_ = (ev.get("player") or {}).get("id")

        if t == "Card" and pid_ is not None:
            if d == "Yellow Card":
                amarillas_ev += 1
            elif d in ("Red Card", "Second Yellow card"):
                rojas_ev += 1

    # Estadísticas (fallback)
    amar_stats = None
    rojas_stats = None
    for st in fix.get("statistics", []) or []:
        for item in (st.get("statistics") or []):
            try:
                v = int(item.get("value") or 0)
            except Exception:
                v = 0
            if item.get("type") == "Yellow Cards":
                amar_stats = (amar_stats or 0) + v
            elif item.get("type") == "Red Cards":
                rojas_stats = (rojas_stats or 0) + v

    amarillas_final = amarillas_ev if amarillas_ev > 0 else amar_stats
    rojas_final = rojas_ev if rojas_ev > 0 else rojas_stats

    return {
        "amarillas_events": amarillas_ev,
        "amarillas_stats": amar_stats,
        "amarillas_final": amarillas_final,
        "rojas_events": rojas_ev,
        "rojas_stats": rojas_stats,
        "rojas_final": rojas_final,
        "eventos_count": len(events),
        "status_short": fix.get("fixture", {}).get("status", {}).get("short"),
        "estado": fix.get("fixture", {}).get("status", {}).get("long"),
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("VERIFICADOR DE AMARILLAS — PLAYOFFS COPA DEL MUNDO 2026")
    print(f"Modo: {'APLICAR CAMBIOS (--apply)' if APPLY else 'SOLO REPORTE (dry-run)'}")
    print("=" * 70)

    # Conectar a BD
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        print("✅ Conectado a BD becbuc\n")
    except Exception as e:
        print(f"❌ No se pudo conectar a BD: {e}")
        sys.exit(1)

    # Query: partidos de playoffs (numero_fifa >= 73) con api_fixture_id, finalizados o en juego
    cur.execute("""
        SELECT
            p.id,
            p.numero_fifa,
            p.api_fixture_id,
            p.estado,
            p.goles_local,
            p.goles_visitante,
            p.amarillas,
            p.rojas,
            p.decisiones_var,
            p.penales_local,
            p.penales_visitante,
            p.datos_confirmados,
            el.nombre AS local,
            ev.nombre AS visitante,
            f.tipo AS fase_tipo
        FROM partido p
        JOIN equipo el ON el.id = p.equipo_local_id
        JOIN equipo ev ON ev.id = p.equipo_visitante_id
        JOIN fase f ON f.id = p.fase_id
        WHERE p.numero_fifa >= 73
          AND p.api_fixture_id IS NOT NULL
          AND p.estado IN ('finalizado', 'en_juego')
        ORDER BY p.numero_fifa
    """)
    partidos = cur.fetchall()
    cols = [desc[0] for desc in cur.description]

    if not partidos:
        print("⚠  No se encontraron partidos KO finalizados con api_fixture_id.")
        print("   Verificá que se ejecutó el auto-mapeo y que los partidos están registrados.")
        cur.close()
        conn.close()
        return

    print(f"Partidos KO a verificar: {len(partidos)}\n")

    diferencias = []
    sin_datos_api = []
    cuota_restante = None

    # Encabezado tabla
    print(f"{'P#':<5} {'Partido':<35} {'Fase':<12} {'BD Amar':>8} {'API Amar':>9} {'Diff':>5} {'Fuente API':>11}")
    print("-" * 90)

    for row in partidos:
        p = dict(zip(cols, row))
        num = p["numero_fifa"]
        fixture_id = p["api_fixture_id"]
        local = p["local"][:15]
        visitante = p["visitante"][:15]
        bd_amar = p["amarillas"]
        bd_rojas = p["rojas"]
        fase = p["fase_tipo"]
        goles = f"{p['goles_local']}-{p['goles_visitante']}"

        # Llamar API-Football
        fix, remaining = fetch_fixture(fixture_id)
        if remaining >= 0:
            cuota_restante = remaining

        if fix is None:
            print(f"P{num:<4} {local} vs {visitante:<20} {'':>8} {'SIN DATOS':>9}")
            sin_datos_api.append(p)
            time.sleep(0.3)
            continue

        parsed = parse_yellow_cards(fix)
        api_amar = parsed["amarillas_final"]
        api_rojas = parsed["rojas_final"]
        eventos = parsed["eventos_count"]
        fuente = "eventos" if parsed["amarillas_events"] > 0 else ("stats" if parsed["amarillas_stats"] is not None else "NULL")

        # Comparar
        bd_val = bd_amar if bd_amar is not None else 0
        api_val = api_amar if api_amar is not None else 0
        diff = api_val - bd_val
        diff_str = f"+{diff}" if diff > 0 else str(diff) if diff != 0 else "  OK"
        marker = " ⚠" if diff != 0 else ""

        partido_str = f"P{num}: {local} vs {visitante}"
        print(f"{'P'+str(num):<5} {partido_str:<35} {fase:<12} {str(bd_amar):>8} {str(api_amar):>9} {diff_str:>5} {fuente:>11}{marker}")

        if diff != 0 and api_amar is not None:
            diferencias.append({
                "partido_id": p["id"],
                "numero_fifa": num,
                "local": p["local"],
                "visitante": p["visitante"],
                "goles": goles,
                "fase": fase,
                "bd_amarillas": bd_amar,
                "api_amarillas": api_amar,
                "bd_rojas": bd_rojas,
                "api_rojas": api_rojas,
                "diff": diff,
                "fuente": fuente,
                "eventos_count": eventos,
                "amarillas_events": parsed["amarillas_events"],
                "amarillas_stats": parsed["amarillas_stats"],
                "status_api": parsed["status_short"],
                "datos_confirmados": p["datos_confirmados"],
            })

        # Pausa para no exceder cuota (max 100/min en plan free, pagado es más)
        time.sleep(0.2)

    print()
    print("=" * 70)
    print(f"RESUMEN: {len(diferencias)} diferencias encontradas / {len(sin_datos_api)} sin datos API")
    if cuota_restante is not None:
        print(f"Cuota API restante: {cuota_restante} requests")
    print()

    if not diferencias:
        print("✅ Todos los partidos tienen el conteo correcto de amarillas.")
    else:
        print("DIFERENCIAS DETALLADAS:")
        print("-" * 70)
        for d in diferencias:
            conf_badge = " [BLINDADO]" if d["datos_confirmados"] else ""
            print(f"\n  P{d['numero_fifa']}: {d['local']} vs {d['visitante']} ({d['goles']}) — {d['fase']}{conf_badge}")
            print(f"    BD:  {d['bd_amarillas']} amarillas, {d['bd_rojas']} rojas")
            print(f"    API: {d['api_amarillas']} amarillas ({d['fuente']}: "
                  f"eventos={d['amarillas_events']}, stats={d['amarillas_stats']})")
            print(f"    Diff: {'+' if d['diff'] > 0 else ''}{d['diff']} amarillas vs BD")
            if d["api_rojas"] != d["bd_rojas"]:
                print(f"    ⚠  Rojas también difieren: BD={d['bd_rojas']} API={d['api_rojas']}")

        print()
        if DRY_RUN:
            print("👉 Para aplicar los cambios ejecutar: python verificar_amarillas_playoffs.py --apply")
        else:
            print("Aplicando actualizaciones en BD...")
            print("-" * 70)
            updated = 0
            errors = 0
            for d in diferencias:
                try:
                    cur.execute("""
                        UPDATE partido
                        SET amarillas = %s
                        WHERE id = %s
                    """, (d["api_amarillas"], d["partido_id"]))
                    print(f"  ✅ P{d['numero_fifa']} {d['local']} vs {d['visitante']}: "
                          f"amarillas {d['bd_amarillas']} → {d['api_amarillas']}")
                    updated += 1
                except Exception as e:
                    print(f"  ❌ P{d['numero_fifa']}: ERROR al actualizar: {e}")
                    errors += 1

            if updated:
                conn.commit()
                print(f"\n✅ {updated} partidos actualizados en BD.")
                print()
                print("⚠  Recordá recalcular puntajes:")
                print("   Portal → Herramientas → Calcular puntajes")
                print("   O bien: POST /api/v1/bets/calcular-puntajes/2")
            else:
                conn.rollback()
            if errors:
                print(f"❌ {errors} errores al actualizar.")

    # Exportar reporte JSON
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = os.path.join(os.path.dirname(__file__), f"becbuc_amarillas_playoffs_{ts}.json")
    report = {
        "timestamp": ts,
        "modo": "apply" if APPLY else "dry-run",
        "total_partidos": len(partidos),
        "diferencias": len(diferencias),
        "sin_datos_api": len(sin_datos_api),
        "cuota_restante": cuota_restante,
        "detalle": diferencias,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Reporte guardado en: {os.path.basename(report_path)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
