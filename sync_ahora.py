"""
sync_ahora.py - Sync INMEDIATO (force) de todos los torneos activos.
Ignora la ventana de fecha/hora: fuerza el sync ahora mismo. Util para
refrescar datos al toque y para ver si los fixtures estan mapeados a la API.
Uso:  python sync_ahora.py            -> todos los torneos activos
      python sync_ahora.py 1 14       -> solo esos torneo_id
"""
import json, sys, urllib.request, urllib.error
from becbuc_config import BASE_URL, ADMIN_USER, ADMIN_PASS

def req(method, url, data=None, token=None):
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")

def main():
    tok = req("POST", f"{BASE_URL}/api/v1/auth/login",
              data={"username": ADMIN_USER, "password": ADMIN_PASS}).get("access_token")
    if not tok:
        print("Login fallo"); return

    ids = [int(x) for x in sys.argv[1:]] if len(sys.argv) > 1 else None
    if ids is None:
        activos = req("GET", f"{BASE_URL}/api/v1/torneo/activas?solo_live=true", token=tok)
        ids = [t["id"] for t in activos if not t.get("cerrado") and t.get("estado_juego") != "terminada"]
        print("Torneos activos:", [(t["id"], t.get("nombre")) for t in activos
                                    if not t.get("cerrado") and t.get("estado_juego") != "terminada"])
    if not ids:
        print("No hay torneos activos para sincronizar."); return

    for tid in ids:
        print(f"\n=== Torneo {tid}: sync FORCE ===")
        try:
            r = req("POST", f"{BASE_URL}/api/v1/bets/sync-resultados/{tid}?force=true&max_detalle=30", token=tok)
            s = r.get("sync", {})
            print(f"  actualizados : {s.get('actualizados', 0)}")
            print(f"  ya finalizados: {s.get('ya_finalizados', 0)}")
            print(f"  sin match API: {s.get('sin_match_api', 0)}   <- si es alto, faltan api_fixture_id (mapeo)")
            print(f"  errores      : {s.get('errores', 0)}")
            print(f"  API calls    : {s.get('api_calls', 0)}")
            print(f"  puntajes_ok  : {r.get('puntajes_ok', False)}")
            am = r.get("auto_mapeo") or s.get("auto_mapeo")
            if am:
                print(f"  auto-mapeo   : {am}")
            for e in s.get("ids_errores", [])[:10]:
                print(f"    err partido {e.get('partido_id')}: {e.get('error')}")
        except Exception as e:
            print(f"  FALLO: {e}")

if __name__ == "__main__":
    main()
