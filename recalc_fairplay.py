"""
recalc_fairplay.py
Cadena completa de recalculo:
  1. sync-historico  → sincroniza todos los resultados finalizados desde API-Football
                       (incluyendo el 3er partido de Paraguay y cualquier otro pendiente)
  2. recalc-fair-play → rellena local/visitante_amarillas/rojas en partido para TODOS
                         los grupos finalizados, luego recalcula participacion.fair_play_pts
  3. Muestra ranking de mejores 8 terceros con columna FP
  4. calcular-puntajes → recalcula scores con standings actualizados

Ejecutar: python recalc_fairplay.py
(requiere que el servidor este corriendo en localhost:8000)
"""
import asyncio, sys, time
import httpx

BASE_URL = "http://localhost:8000"
USER     = "jose"
PASS     = "catalina"
TORNEO   = 2


async def login(client):
    r = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": USER, "password": PASS},
    )
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("Login fallido -- sin token")
    return token


async def main():
    async with httpx.AsyncClient(timeout=180) as client:
        print("Autenticando...")
        token = await login(client)
        hdrs  = {"Authorization": f"Bearer {token}"}

        # -----------------------------------------------------------------
        # PASO 1: Sync historico -- trae TODOS los resultados finalizados
        # incluyendo el ultimo partido de Paraguay y cualquier pendiente
        # -----------------------------------------------------------------
        print("\nPASO 1: Sincronizando resultados desde API-Football...")
        print("   (sync-historico con force=True, max_detalle=50)")
        t0 = time.time()
        r1 = await client.post(
            f"{BASE_URL}/api/v1/bets/sync-historico/{TORNEO}",
            params={"max_detalle": 50},
            headers=hdrs,
        )
        t1 = time.time() - t0

        if r1.status_code != 200:
            print(f"ERROR HTTP {r1.status_code}: {r1.text[:400]}")
            sys.exit(1)

        s1 = r1.json()
        actualizados = s1.get("actualizados", "?")
        bracket_ok   = s1.get("bracket_ok", False)
        puntajes_ok  = s1.get("puntajes_ok", False)
        print(f"   OK en {t1:.1f}s:")
        print(f"      Partidos actualizados : {actualizados}")
        print(f"      Bracket avanzado      : {'OK' if bracket_ok else 'FALLO'}")
        print(f"      Puntajes recalculados  : {'OK' if puntajes_ok else 'FALLO'}")
        if s1.get("bracket_error"):
            print(f"      AVISO Bracket: {s1['bracket_error']}")
        if s1.get("participacion_error"):
            print(f"      AVISO Participacion: {s1['participacion_error']}")
        if s1.get("puntajes_error"):
            print(f"      AVISO Puntajes: {s1['puntajes_error']}")

        # -----------------------------------------------------------------
        # PASO 2: Recalc fair play -- rellena tarjetas por equipo en partido
        # + recalcula participacion.fair_play_pts
        # -----------------------------------------------------------------
        print("\nPASO 2: Cargando tarjetas por equipo desde API-Football...")
        print("   (consulta 1 fixture por partido, en lotes de 10 -- puede tardar 60-90s)")
        t0 = time.time()
        r2 = await client.post(
            f"{BASE_URL}/api/v1/bets/recalc-fair-play/{TORNEO}",
            params={"max_partidos": 100},
            headers=hdrs,
        )
        t2 = time.time() - t0

        if r2.status_code != 200:
            print(f"ERROR HTTP {r2.status_code}: {r2.text[:400]}")
            sys.exit(1)

        s2 = r2.json()
        print(f"   OK en {t2:.1f}s:")
        print(f"      Partidos procesados : {s2.get('partidos_procesados', '?')}")
        print(f"      Actualizados        : {s2.get('actualizados', '?')}")
        print(f"      API calls usadas    : {s2.get('api_calls', '?')}")
        print(f"      Fair play recalc    : {'OK' if s2.get('fair_play_recalculado') else 'FALLO'}")
        if s2.get("errores"):
            errs = s2["errores"]
            print(f"      Errores ({len(errs)}): {errs[:3]}")

        if not s2.get("fair_play_recalculado"):
            print("\nAVISO: Fair play no pudo recalcularse. Ver errores arriba.")

        # -----------------------------------------------------------------
        # PASO 3: Ver ranking de mejores 8 terceros con FP
        # -----------------------------------------------------------------
        print("\nPASO 3: Ranking mejores 8 terceros (criterio FIFA + Fair Play)...")
        r3 = await client.get(
            f"{BASE_URL}/api/v1/bets/fair-play-terceros/{TORNEO}",
            headers=hdrs,
        )
        if r3.status_code != 200:
            print(f"ERROR HTTP {r3.status_code}: {r3.text[:300]}")
        else:
            fp = r3.json()
            if fp.get("aviso"):
                print(f"   AVISO: {fp['aviso']}")
            else:
                ranking = fp.get("ranking", [])
                SEP = "-" * 105
                print()
                print("=" * 105)
                print("  RANKING MEJORES 8 TERCEROS -- criterio FIFA: Pts -> DG -> GF -> FP(menor) -> FIFA Ranking -> Grupo")
                print("=" * 105)
                print(f"  {'#':<4} {'Gpo':<5} {'Equipo':<24} {'PJ':>3} {'PG':>3} {'PE':>3} {'PP':>3} "
                      f"{'GF':>3} {'GC':>3} {'DG':>4} {'Pts':>4} {'FP':>4} {'FIFA':>5}  Clasifica")
                print(SEP)
                for t in ranking:
                    if t["pos"] == 9:
                        print(SEP)
                    cls   = "CLASIFICA" if t["clasifica"] else "ELIMINADO"
                    dg    = f"+{t['dg']}" if t['dg'] >= 0 else str(t['dg'])
                    fp_v  = t.get("fair_play_pts", 0) or 0
                    fifa_s = str(t["fifa_ranking"]) if t.get("fifa_ranking") else "--"
                    gc    = t["gf"] - t["dg"]
                    print(f"  {t['pos']:<4} {t['grupo']:<5} {str(t['equipo'])[:24]:<24} "
                          f"{t['pj']:>3} {t['pg']:>3} {t['pe']:>3} {t['pp']:>3} "
                          f"{t['gf']:>3} {gc:>3} {dg:>4} {t['pts']:>4} "
                          f"{fp_v:>4} {fifa_s:>5}  {cls}")
                print()
                print(f"  CLASIFICAN: {', '.join(fp.get('clasifican', []))}")
                print(f"  ELIMINADOS: {', '.join(fp.get('eliminados', []))}")
                print()

        # -----------------------------------------------------------------
        # PASO 4: Recalcular puntajes de apostadores
        # -----------------------------------------------------------------
        print("PASO 4: Recalculando puntajes de apostadores...")
        r4 = await client.post(
            f"{BASE_URL}/api/v1/bets/calcular-puntajes/{TORNEO}",
            headers=hdrs,
        )
        if r4.status_code == 200:
            rd = r4.json()
            procesados = rd.get("procesados", rd.get("puntajes_procesados", "?"))
            print(f"   OK: {procesados} apostadores recalculados")
        else:
            print(f"   AVISO HTTP {r4.status_code} -- puntajes no actualizados (no critico para fair play)")

        print("\nProceso completo:")
        print("  - Paraguay y todos los grupos actualizados")
        print("  - Fair play por equipo cargado desde API-Football")
        print("  - Tab '3ros' en becbuc-live.html mostrara FP")
        print("  - Bracket 16avos actualizado con los mejores 8 terceros\n")


if __name__ == "__main__":
    asyncio.run(main())
