import requests
import json

BASE = "http://localhost:8000"

# Login
r = requests.post(f"{BASE}/api/v1/auth/login", json={"username": "jose", "password": "catalina"})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("Login OK")

# Recalcular puntajes
r2 = requests.post(f"{BASE}/api/v1/bets/calcular-puntajes/2", headers=headers)
data = r2.json()
print(f"Status: {r2.status_code}")
print(f"Procesados: {data.get('procesados', '?')}")
print(f"Plenos: {data.get('plenos', '?')}")
print(f"Aciertos: {data.get('aciertos', '?')}")
print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
