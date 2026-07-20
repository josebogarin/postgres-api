"""
Diagnostica P90 y fuerza sync desde API-Football.
Ejecutar con uvicorn activo en puerto 8000.
"""
import json, urllib.request, urllib.error, sys

BASE = 'http://localhost:8000'

def api_json(url, method='GET', token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=b'' if method == 'POST' else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:400]}")
        return None

def login():
    data = json.dumps({'username': 'jose', 'password': 'catalina'}).encode()
    req = urllib.request.Request(f'{BASE}/api/v1/auth/login',
                                  data=data,
                                  headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())['access_token']

def sep(title=''):
    print()
    print('=' * 55)
    if title:
        print(f'  {title}')
        print('=' * 55)

# ──────────────────────────────────────────────
sep('LOGIN')
try:
    token = login()
    print('  OK')
except Exception as e:
    print(f'  FALLO: {e}')
    sys.exit(1)

# ──────────────────────────────────────────────
sep('CONSULTA P90 EN API-FOOTBALL (solo lectura)')
print('  GET /consulta-partido/90 ...')
consulta = api_json(f'{BASE}/api/v1/bets/consulta-partido/90', token=token)
if consulta:
    if not consulta.get('ok'):
        print(f"  ERROR: {consulta.get('error')}")
    bd  = consulta.get('bd', {})
    api = consulta.get('api', {})
    print(f"\n  [BD actual]")
    print(f"    Estado:        {bd.get('bd_estado')}")
    print(f"    Goles:         {bd.get('bd_goles')}")
    print(f"    api_fixture_id:{bd.get('api_fixture_id')} {'✅' if bd.get('api_fixture_id') else '❌ SIN MAPEO'}")
    print(f"    confirmado:    {bd.get('datos_confirmados')}")
    print(f"    amarillas:     {bd.get('bd_amarillas')}")
    print(f"    rojas:         {bd.get('bd_rojas')}")
    print(f"    VAR:           {bd.get('bd_var')}")
    print(f"    minuto_gol:    {bd.get('bd_minuto_gol')}")
    print(f"    pen_partido:   {bd.get('bd_penales_partido')}")
    print(f"    pen_tanda:     {bd.get('bd_penales_tanda')}")

    if api:
        print(f"\n  [API-Football]")
        print(f"    Estado:        {api.get('estado')} ({api.get('status_short')})")
        print(f"    Goles:         {api.get('goles_local')}-{api.get('goles_visitante')}")
        print(f"    pen_tanda:     {api.get('penales_tanda_local')}-{api.get('penales_tanda_visitante')}")
        print(f"    amarillas:     {api.get('amarillas')}")
        print(f"    rojas:         {api.get('rojas')}")
        print(f"    VAR:           {api.get('decisiones_var')}")
        print(f"    minuto_gol:    {api.get('minuto_primer_gol')}")
        print(f"    pen_partido:   {api.get('penales_partido')}")
        print(f"    eventos:       {api.get('eventos_count')}")
        print(f"    cuota restante:{api.get('cuota_restante')}")

    diffs = consulta.get('diferencias', {})
    if diffs:
        print(f"\n  ⚠️  Diferencias BD vs API-Football:")
        for campo, vals in diffs.items():
            print(f"    {campo}: BD={vals['bd']} | API={vals['api']}")
    else:
        print(f"\n  ✅ BD y API-Football coinciden")
else:
    print('  Endpoint no disponible — ¿reiniciaste uvicorn?')
    sys.exit(1)

# ──────────────────────────────────────────────
sep('SYNC P90 DESDE API-FOOTBALL (escribe en BD)')
print('  POST /sync-partido/90 ...')
print('  (actualiza goles, amarillas, VAR, minuto, bracket y puntajes)')
sync = api_json(f'{BASE}/api/v1/bets/sync-partido/90', method='POST', token=token)
if sync:
    if not sync.get('ok'):
        print(f"  ERROR: {sync.get('error')}")
    else:
        print(f"  Partido:        {sync.get('partido')}")
        print(f"  Estado API:     {sync.get('estado_api')}")
        print(f"  Goles:          {sync.get('goles')}")
        print(f"  Items API:      {sync.get('api_items')}")
        print(f"  Bracket OK:     {sync.get('bracket_ok')}")
        print(f"  Puntajes OK:    {sync.get('puntajes_ok')}")
        print(f"  Cuota restante: {sync.get('cuota_restante')}")
        p = sync.get('puntajes', {})
        if p:
            print(f"  Plenos: {p.get('plenos')} | Aciertos: {p.get('aciertos')}")
else:
    print('  Falló (ver log uvicorn)')

sep()
print('  Listo.')
print()
