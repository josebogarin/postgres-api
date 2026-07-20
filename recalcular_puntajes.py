import urllib.request, urllib.parse, json

data = urllib.parse.urlencode({"username":"jose","password":"catalina"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(req, timeout=15) as r:
    token = json.loads(r.read())["access_token"]
print("Login OK")

req2 = urllib.request.Request(
    "http://localhost:8000/api/v1/bets/calcular-puntajes/2",
    method="POST",
    headers={"Authorization": "Bearer " + token, "Content-Length": "0"}
)
with urllib.request.urlopen(req2, timeout=120) as r2:
    res = json.loads(r2.read())

print(f"plenos={res.get('plenos')} aciertos={res.get('aciertos')} fallos={res.get('fallos')}")
print(f"globales={res.get('globales_procesadas')}")
for k, v in (res.get("por_fase") or {}).items():
    print(f"  {k}: {v}")
