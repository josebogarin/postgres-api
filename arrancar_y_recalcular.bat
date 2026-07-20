@echo off
echo Arrancando uvicorn...
cd /d "C:\proyecto FAST API\backend"
start "BECBUC-Server" cmd /k ".venv\Scripts\activate.bat && uvicorn app.main:app --reload --port 8000"
echo Esperando 15 segundos para que inicie el servidor...
timeout /t 15 /nobreak
echo Haciendo login...
python -c "
import urllib.request, json, time

# Login
data = json.dumps({'username':'jose','password':'catalina'}).encode()
req = urllib.request.Request('http://localhost:8000/api/v1/auth/login', data=data, headers={'Content-Type':'application/json'})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())['access_token']
print('Login OK')

# Calcular puntajes
req2 = urllib.request.Request('http://localhost:8000/api/v1/bets/calcular-puntajes/2', method='POST', headers={'Authorization': f'Bearer {token}', 'Content-Type':'application/json'})
resp2 = urllib.request.urlopen(req2)
result = json.loads(resp2.read())
print('RESULTADO RECALCULO:')
print(json.dumps(result, indent=2, ensure_ascii=False))
"
pause
