@echo off
echo Recalculando puntajes (Mayor Goleada deshabilitada)...
cd /d "C:\proyecto FAST API\backend"
call .venv\Scripts\activate.bat

python -c "
import requests, json, sys
BASE = 'http://localhost:8000'
r = requests.post(f'{BASE}/api/v1/auth/login', json={'username':'jose','password':'catalina'})
if r.status_code != 200:
    print('ERROR login:', r.text); sys.exit(1)
token = r.json()['access_token']
print('Login OK')

r2 = requests.post(f'{BASE}/api/v1/bets/calcular-puntajes/2',
     headers={'Authorization': f'Bearer {token}'})
if r2.status_code != 200:
    print('ERROR calcular:', r2.text); sys.exit(1)
res = r2.json()
print('Recalculo OK')
print('  Partidos procesados:', res.get('partidos_procesados','?'))
print('  Globales procesadas:', res.get('globales_procesadas','?'))
print()
print('Item E (Mayor Goleada) = 0 para todos.')
print('Se reactivara al finalizar el campeonato.')
"

pause
