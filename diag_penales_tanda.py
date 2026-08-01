"""
Diagnóstico: elapsed times de penales en P74 y P75 desde API-Football.
Ejecutar desde: C:\proyecto FAST API\backend
  .venv\Scripts\Activate.ps1
  cd ..
  python diag_penales_tanda.py
"""
import os as _osp
_BASE = _osp.path.dirname(_osp.path.abspath(__file__))
import asyncio, sys
sys.path.insert(0, _osp.path.join(_BASE, 'backend'))

import httpx
from app.core.config import settings

API_BASE = "https://v3.football.api-sports.io"
API_KEY = settings.APIFOOTBALL_KEY

async def check_fixture(num_fifa, fix_id):
    if not fix_id:
        print(f"P{num_fifa}: sin api_fixture_id, skip")
        return
    print(f"\n=== P{num_fifa} (fixture {fix_id}) ===")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{API_BASE}/fixtures", params={"id": fix_id},
                             headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": "v3.football.api-sports.io"})
        data = r.json()
        if not data.get("response"):
            print(f"  Sin respuesta: {data}")
            return
        fix = data["response"][0]
        status = fix["fixture"]["status"]["short"]
        goals_h = fix["goals"]["home"]
        goals_a = fix["goals"]["away"]
        pen_h = fix["score"]["penalty"]["home"]
        pen_a = fix["score"]["penalty"]["away"]
        print(f"  Estado: {status} | Goles: {goals_h}-{goals_a} | Tanda: {pen_h}-{pen_a}")
        events = fix.get("events", [])
        print(f"  Total events: {len(events)}")
        penalty_events = [
            ev for ev in events
            if any(kw in (ev.get("type","") + ev.get("detail","")).lower()
                   for kw in ["penalty","penalt"])
        ]
        print(f"  Penalty events ({len(penalty_events)}):")
        count_in_play = 0
        for ev in sorted(penalty_events, key=lambda e: (e.get("time",{}).get("elapsed") or 0)):
            elapsed = ev.get("time", {}).get("elapsed")
            extra   = ev.get("time", {}).get("extra")
            t       = ev.get("type", "")
            d       = ev.get("detail", "")
            team    = ev.get("team", {}).get("name", "?")
            player  = ev.get("player", {}).get("name", "?")
            in_play = elapsed is not None and elapsed <= 120
            if in_play:
                count_in_play += 1
            print(f"    elapsed={elapsed} extra={extra} {'IN-PLAY' if in_play else 'TANDA'} | {t}/{d} | {team} | {player}")
        print(f"  penales_partido correcto (filtro elapsed<=120): {count_in_play}")
        print(f"  penales_partido actual (sin filtro): {len(penalty_events)}")

async def main():
    # P74: Germany vs Paraguay
    fixtures = {74: 1565176, 75: None}
    
    # Get P75 fixture ID from DB
    try:
        import asyncpg
        conn = await asyncpg.connect("postgresql://app_user:Bec_app_2025@localhost:5433/becbuc")
        row = await conn.fetchrow("SELECT api_fixture_id FROM partido WHERE numero_fifa=75")
        await conn.close()
        if row:
            fixtures[75] = row["api_fixture_id"]
    except Exception as e:
        print(f"DB error (P75 fixture): {e}")
        # Default known value if available
        fixtures[75] = None

    for num, fid in fixtures.items():
        await check_fixture(num, fid)

if __name__ == "__main__":
    asyncio.run(main())
