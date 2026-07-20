"""
Diagnóstico: estructura de eventos Card en API-Football (eventos_api guardados en BD).
Muestra todos los eventos de tipo 'Card' de partidos finalizados del torneo 2.
Objetivo: identificar si se puede distinguir tarjetas a jugadores de campo vs banco/staff.

Ejecutar: cd "C:\proyecto FAST API\backend" && .venv\Scripts\python.exe ..\diagnostico_tarjetas_api.py
"""
import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://app_user@localhost:5432/becbuc"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        r = await conn.execute(text("""
            SELECT p.id, p.numero_fifa,
                   eq_l.nombre AS local, p.goles_local,
                   p.goles_visitante, eq_v.nombre AS visitante,
                   p.amarillas, p.rojas,
                   p.eventos_api
            FROM partido p
            JOIN equipo eq_l ON p.equipo_local_id = eq_l.id
            JOIN equipo eq_v ON p.equipo_visitante_id = eq_v.id
            JOIN fase f ON p.fase_id = f.id
            WHERE f.torneo_id = 2
              AND p.estado = 'finalizado'
              AND p.eventos_api IS NOT NULL
              AND jsonb_array_length(p.eventos_api) > 0
              AND p.amarillas > 0
            ORDER BY p.numero_fifa
            LIMIT 20
        """))
        rows = r.fetchall()

        print(f"\n=== EVENTOS CARD EN API-FOOTBALL ===")
        print(f"Partidos con eventos_api y amarillas > 0: {len(rows)}")

        # Recolectar todos los campos únicos que aparecen en eventos Card
        all_card_fields: dict[str, set] = {}
        has_player_null = 0
        has_comments = 0
        total_cards = 0
        coach_cards_found = []

        for row in rows:
            pid, num, local, gl, gv, visitante, amarillas_bd, rojas_bd, eventos_api = row
            if not eventos_api:
                continue

            events = eventos_api if isinstance(eventos_api, list) else json.loads(eventos_api)
            card_events = [e for e in events if e.get("type") == "Card"]

            if not card_events:
                continue

            print(f"\nP{num} | {local} {gl}-{gv} {visitante} | BD: {amarillas_bd}🟨 {rojas_bd}🟥 | {len(card_events)} card events")

            for ev in card_events:
                total_cards += 1
                detail = ev.get("detail", "")
                player = ev.get("player", {}) or {}
                assist = ev.get("assist", {}) or {}
                comments = ev.get("comments")
                player_id = player.get("id")
                player_name = player.get("name", "?")
                team_name = (ev.get("team") or {}).get("name", "?")
                elapsed = (ev.get("time") or {}).get("elapsed", "?")

                if player_id is None:
                    has_player_null += 1
                if comments:
                    has_comments += 1
                    if any(k in str(comments).lower() for k in ["coach", "bench", "staff", "technical"]):
                        coach_cards_found.append({
                            "partido": f"P{num} {local}-{visitante}",
                            "detail": detail,
                            "player_id": player_id,
                            "player_name": player_name,
                            "comments": comments,
                            "team": team_name,
                            "elapsed": elapsed,
                        })

                # Mostrar campos disponibles
                for k in ev.keys():
                    if k not in all_card_fields:
                        all_card_fields[k] = set()
                    all_card_fields[k].add(str(ev[k])[:50] if ev[k] is not None else "null")

                print(f"  min{elapsed} | {detail} | player_id={player_id} | player={player_name} | team={team_name} | comments={comments!r}")

                # Mostrar todos los campos del evento (primera tarjeta detallada)
                if total_cards <= 3:
                    print(f"  → FULL EVENT KEYS: {list(ev.keys())}")

        print(f"\n=== RESUMEN ===")
        print(f"Total Card events analizados: {total_cards}")
        print(f"  Con player_id = NULL:  {has_player_null}")
        print(f"  Con campo 'comments':  {has_comments}")
        print(f"\nCampos disponibles en eventos Card:")
        for k, vals in sorted(all_card_fields.items()):
            sample_vals = list(vals)[:3]
            print(f"  {k}: {sample_vals}")

        if coach_cards_found:
            print(f"\n⚠  COACH/BENCH CARDS identificados ({len(coach_cards_found)}):")
            for cc in coach_cards_found:
                print(f"  {cc}")
        else:
            print(f"\nℹ  No se encontraron tarjetas con comments='Coach'/'Bench'/etc.")
            print("   Puede que API-Football no distinga banco/staff vía 'comments'.")

    await engine.dispose()

asyncio.run(main())
# NOTE: Run diagnostico_tarjetas_api.py first to see actual field structure before fixing.
