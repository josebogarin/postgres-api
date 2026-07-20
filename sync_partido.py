# -*- coding: utf-8 -*-
"""
sync_partido.py <numero_fifa>
Finaliza y SINCRONIZA un partido individual desde API-Football:
  1) GET  /consulta-partido/{nf}   (estado BD vs API, solo lectura)
  2) POST /sync-partido/{nf}        (auto-mapea api_fixture_id si falta, trae goles + items
                                     J/K/L/M/N/tanda, avanza bracket, recalcula puntajes)
  3) GET  /consulta-partido/{nf}    (verificacion despues del sync)

Sirve cuando un partido termino pero la API no cargo los items automaticamente
(quedaron NULL). Requiere uvicorn en :8000.

Uso:
  backend\\.venv\\Scripts\\python.exe sync_partido.py 103
"""
import json, urllib.request, urllib.error, sys

BASE = 'http://localhost:8000'
NF = sys.argv[1] if len(sys.argv) > 1 else '103'

def api_json(url, method='GET', token=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=b'' if method == 'POST' else None)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:400]}"); return None
    except Exception as e:
        print(f"  ERROR: {e}"); return None

def login():
    data = json.dumps({'username': 'jose', 'password': 'catalina'}).encode()
    req = urllib.request.Request(f'{BASE}/api/v1/auth/login', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']

def sep(t=''):
    print('\n' + '=' * 58)
    if t: print(f'  {t}'); print('=' * 58)

def show_consulta(c):
    if not c:
        print("  (sin respuesta)"); return
    if not c.get('ok'):
        print(f"  ERROR: {c.get('error')}")
    bd = c.get('bd', {}); api = c.get('api', {}); dif = c.get('diferencias', {})
    print("  [BD]  estado=%s goles=%s fixture=%s confirmado=%s" % (
        bd.get('bd_estado'), bd.get('bd_goles'),
        bd.get('api_fixture_id') or 'SIN MAPEO', bd.get('datos_confirmados')))
    print("  [API] estado=%s goles=%s | amar=%s rojas=%s VAR=%s penJuego=%s min1er=%s" % (
        api.get('api_estado'), api.get('api_goles'), api.get('amarillas'),
        api.get('rojas'), api.get('var'), api.get('penales_partido'),
        api.get('minuto_primer_gol')))
    if dif:
        print("  DIFERENCIAS BD vs API:")
        for campo, d in dif.items():
            print(f"    {campo}: bd={d.get('bd')} api={d.get('api')}")

print("=" * 58)
print(f"  SYNC PARTIDO P{int(NF):03d}  (API-Football -> BD)")
print("=" * 58)

sep('LOGIN')
try:
    token = login(); print('  OK')
except Exception as e:
    sys.exit(f'  FALLO login (uvicorn en :8000?): {e}')

sep(f'ANTES - GET /consulta-partido/{NF}')
show_consulta(api_json(f'{BASE}/api/v1/bets/consulta-partido/{NF}', token=token))

sep(f'SYNC - POST /sync-partido/{NF}')
s = api_json(f'{BASE}/api/v1/bets/sync-partido/{NF}', method='POST', token=token)
if s:
    if s.get('ok'):
        print(f"  OK  goles={s.get('goles')}  bracket_ok={s.get('bracket_ok')}  puntajes_ok={s.get('puntajes_ok')}")
        it = s.get('api_items') or {}
        if it:
            print(f"  items: {it}")
        p = s.get('partido')
        if p: print(f"  partido: {p}")
    else:
        print(f"  NO OK -> {s}")

sep(f'DESPUES - GET /consulta-partido/{NF}')
show_consulta(api_json(f'{BASE}/api/v1/bets/consulta-partido/{NF}', token=token))

print("\nListo. Si aun quedan items en NULL, correr de nuevo cuando el partido")
print("este 'finalizado' en API-Football (tras el pitazo final / alargue / penales).")
