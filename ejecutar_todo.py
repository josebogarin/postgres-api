"""
BECBUC - Ejecutar Todo: Sync + Avanzar Bracket + Calcular Puntajes
Doble click para correr (requiere uvicorn activo en puerto 8000).
"""
import requests, sys, json

def get_base():
    """Intenta localhost primero, luego ngrok."""
    try:
        requests.get("http://localhost:8000/docs", timeout=3)
        return "http://localhost:8000/api/v1"
    except Exception:
        pass
    # Try ngrok
    try:
        r = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
        for t in r.json().get("tunnels", []):
            if t.get("proto") == "https":
                return t["public_url"] + "/api/v1"
    except Exception:
        pass
    return None

def run():
    print("=" * 45)
    print(" BECBUC - Sync + Bracket + Puntajes")
    print("=" * 45)

    BASE = get_base()
    if not BASE:
        print("\n❌ No se puede conectar a http://localhost:8000")
        print("   Verificá que uvicorn esté activo:")
        print("   cd backend && .venv\\Scripts\\Activate && uvicorn app.main:app --reload --port 8000")
        return

    print(f"\nConectado a: {BASE}\n")

    # Login
    print("[1/4] Autenticando...")
    r = requests.post(f"{BASE}/auth/login", data={"username": "jose", "password": "catalina"},
                      headers={"ngrok-skip-browser-warning": "true"})
    if r.status_code != 200:
        print(f"  ❌ Login falló: {r.status_code}")
        return
    token = r.json().get("access_token")
    HDR = {"Authorization": f"Bearer {token}", "ngrok-skip-browser-warning": "true"}
    print("  ✅ OK")

    # Sync
    print("[2/4] Sincronizando desde API-Football...")
    try:
        r = requests.post(f"{BASE}/bets/sync-resultados/2", headers=HDR, timeout=90)
        d = r.json()
        act = d.get("actualizados", [])
        n = len(act) if isinstance(act, list) else act
        print(f"  ✅ actualizados={n} | bracket_ok={d.get('bracket_ok')} | puntajes_ok={d.get('puntajes_ok')}")
        s = d.get("sync", {})
        if s.get("puntajes_error"):
            print(f"  ⚠️  puntajes_error: {s['puntajes_error']}")
        if s.get("bracket_error"):
            print(f"  ⚠️  bracket_error: {s['bracket_error']}")
        p = d.get("puntajes", {})
        if p:
            print(f"     plenos={p.get('plenos')} | aciertos={p.get('aciertos')}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

    # Avanzar bracket
    print("[3/4] Avanzando bracket KO...")
    try:
        r = requests.post(f"{BASE}/bets/avanzar-bracket/2", headers=HDR, timeout=30)
        d = r.json()
        print(f"  ✅ {d.get('mensaje', d)}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

    # Calcular puntajes
    print("[4/4] Calculando puntajes...")
    try:
        r = requests.post(f"{BASE}/bets/calcular-puntajes/2", headers=HDR, timeout=90)
        d = r.json()
        if "detail" in d:
            print(f"  ❌ ERROR: {d['detail']}")
        else:
            print(f"  ✅ plenos={d.get('plenos')} | aciertos={d.get('aciertos')} | fallos={d.get('fallos')}")
            gp = d.get("globales_procesadas") or d.get("globales", {}).get("procesadas")
            if gp is not None:
                print(f"     globales procesadas={gp}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

    print("\n" + "=" * 45)
    print("  LISTO. Recargá el portal para ver cambios.")
    print("=" * 45)

if __name__ == "__main__":
    run()
    input("\nPresioná Enter para cerrar...")
