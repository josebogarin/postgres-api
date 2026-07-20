"""
Diagnóstico VAR vía ESPN API no oficial
Busca France vs Senegal en el scoreboard ESPN del 16/06/2026,
obtiene el summary + play-by-play y cuenta menciones de VAR.

Ejecutar (desde C:\proyecto FAST API, con venv activado):
  python diag_var_espn.py [game_id_opcional]

No requiere API key.
"""
import urllib.request, json, sys, re

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def find_france_senegal():
    """Busca el game_id de Francia vs Senegal en el scoreboard del 16/06."""
    url = f"{BASE}/scoreboard?dates=20260616"
    print(f"Fetching scoreboard: {url}")
    data = get(url)
    events = data.get("events", [])
    print(f"Partidos encontrados: {len(events)}")
    for ev in events:
        name = ev.get("name", "")
        eid  = ev.get("id", "")
        comp = ev.get("competitions", [{}])[0]
        teams = " vs ".join(
            c.get("team", {}).get("displayName", "?")
            for c in comp.get("competitors", [])
        )
        status = comp.get("status", {}).get("type", {}).get("description", "?")
        print(f"  id={eid:>12s}  {teams:40s}  {status}")
        if "france" in name.lower() and "senegal" in name.lower():
            return eid
    return None


def analyze_summary(game_id):
    """Descarga summary + playByPlay y analiza VAR."""
    url = f"{BASE}/summary?event={game_id}"
    print(f"\nFetching summary: {url}")
    data = get(url)

    # ── Estadísticas (amarillas, rojas) ──────────────────────────────────
    print("\n=== ESTADÍSTICAS ===")
    for team_stats in data.get("boxscore", {}).get("teams", []):
        team_name = team_stats.get("team", {}).get("displayName", "?")
        for stat in team_stats.get("statistics", []):
            if stat.get("name") in ("yellowCards", "redCards", "fouls", "offsides"):
                print(f"  {team_name:20s}  {stat['name']:15s}  {stat.get('displayValue', stat.get('value'))}")

    # ── Plays / Commentary ───────────────────────────────────────────────
    print("\n=== PLAY-BY-PLAY (eventos VAR) ===")
    plays = data.get("plays", [])
    if not plays:
        # Algunos endpoints lo ponen en commentary
        plays = data.get("commentary", [])
    print(f"Total plays/events: {len(plays)}")

    VAR_PATTERNS = re.compile(
        r"VAR|video review|goes to monitor|referee check|review stand|ruled out.*review|"
        r"overturned|upheld.*review|check.*video|monitor.*review",
        re.IGNORECASE
    )

    var_events = []
    card_events = []
    goal_events = []

    for play in plays:
        text = play.get("text", play.get("commentary", play.get("description", "")))
        minute = play.get("clock", {}).get("displayValue", play.get("wallclock", "?"))
        ptype  = play.get("type", {}).get("text", play.get("type", ""))

        if VAR_PATTERNS.search(text):
            var_events.append((minute, text[:120]))
        if any(k in str(ptype).lower() for k in ("yellow", "card", "foul")):
            card_events.append((minute, ptype, text[:80]))
        if "goal" in str(ptype).lower():
            goal_events.append((minute, ptype, text[:80]))

    print(f"\n── Goles ({len(goal_events)}) ──")
    for m, t, txt in goal_events:
        print(f"  {m:6s}  {t:20s}  {txt}")

    print(f"\n── Tarjetas ({len(card_events)}) ──")
    for m, t, txt in card_events:
        print(f"  {m:6s}  {t:20s}  {txt}")

    print(f"\n── VAR menciones ({len(var_events)}) ──")
    for m, txt in var_events:
        print(f"  {m:6s}  {txt}")

    # ── Guardar respuesta completa ───────────────────────────────────────
    out = f"diag_espn_{game_id}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nRespuesta completa guardada en: {out}")

    print(f"\n=== RESUMEN ===")
    print(f"  VAR menciones en commentary: {len(var_events)}")
    print(f"  Tarjetas detectadas:         {len(card_events)}")
    print(f"  Goles detectados:            {len(goal_events)}")


def main():
    if len(sys.argv) > 1:
        game_id = sys.argv[1]
        print(f"Usando game_id={game_id} pasado por argumento")
    else:
        game_id = find_france_senegal()
        if not game_id:
            print("\nNo se encontró France vs Senegal en el scoreboard del 16/06.")
            print("Probá: python diag_var_espn.py <game_id>")
            print("Buscá el game_id en: https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=20260616")
            return

    analyze_summary(game_id)


if __name__ == "__main__":
    main()
