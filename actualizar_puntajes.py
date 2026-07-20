"""
Sincroniza resultados desde API-Football y recalcula puntajes.
Ejecutar con el venv activo en la carpeta del proyecto.
"""
import urllib.request, json, urllib.parse, sys

BASE = 'http://localhost:8000/api/v1'

def main():
    # Login
    print("Conectando...")
    data = json.dumps({'username': 'jose', 'password': 'catalina'}).encode()
    req0 = urllib.request.Request(BASE + '/auth/login', data=data,
                                   headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req0, timeout=10)
        token = json.loads(r.read())['access_token']
        print("Login OK")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"ERROR login {e.code}: {body[:500]}")
        input("Presiona Enter para cerrar...")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR login: {e}")
        input("Presiona Enter para cerrar...")
        sys.exit(1)

    headers = {'Authorization': 'Bearer ' + token, 'Content-Length': '0'}

    # Sync
    print("\nSincronizando resultados (puede tardar ~30s)...")
    try:
        req = urllib.request.Request(BASE + '/bets/sync-resultados/2?force=true&max_detalle=50',
                                     method='POST', headers=headers, data=b'')
        r = urllib.request.urlopen(req, timeout=120)
        s = json.loads(r.read())
        print(f"  Actualizados: {s.get('actualizados', '?')}")
        print(f"  Bracket OK:   {s.get('bracket_ok', '?')}")
        print(f"  Puntajes OK:  {s.get('puntajes_ok', '?')}")
        p = s.get('puntajes', {})
        if p:
            print(f"  Procesados:   {p.get('procesados', '?')}, Plenos: {p.get('plenos', '?')}, Aciertos: {p.get('aciertos', '?')}")
    except Exception as e:
        print(f"ERROR sync: {e}")
        # Intentar solo recalcular
        print("\nIntentando solo recalcular puntajes...")
        try:
            req2 = urllib.request.Request(BASE + '/bets/calcular-puntajes/2',
                                          method='POST', headers=headers, data=b'')
            r2 = urllib.request.urlopen(req2, timeout=60)
            p2 = json.loads(r2.read())
            print(f"  Procesados: {p2.get('procesados', '?')}, Plenos: {p2.get('plenos', '?')}, Aciertos: {p2.get('aciertos', '?')}")
        except Exception as e2:
            print(f"ERROR recalcular: {e2}")

    print("\nListo.")
    input("Presiona Enter para cerrar...")

if __name__ == '__main__':
    main()
