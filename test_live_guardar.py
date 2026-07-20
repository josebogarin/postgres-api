# -*- coding: utf-8 -*-
"""test PIN = primer nombre (no escribe apuestas reales)."""
import sys, os
try:
    import requests
except ImportError:
    os.system(f'"{sys.executable}" -m pip install requests --quiet'); import requests
try:
    import psycopg2
except ImportError:
    os.system(f'"{sys.executable}" -m pip install psycopg2-binary --quiet'); import psycopg2

API = "http://localhost:8000/api/v1"
APOSTADOR_ID = 15
CONN_APP = "host=localhost port=5432 dbname=app_db user=app_user password=superpassword"

c = psycopg2.connect(CONN_APP); cur = c.cursor()
cur.execute("SELECT username, nombre FROM users WHERE id=%s", (APOSTADOR_ID,))
row = cur.fetchone(); c.close()
username, nombre = row[0], (row[1] or "")
primer = nombre.split()[0] if nombre.strip() else username
print(f"id={APOSTADOR_ID} username={username!r} nombre={nombre!r} primer_nombre={primer!r}")

lr = requests.post(f"{API}/auth/login", json={"username":"jose","password":"catalina"}, timeout=30)
hdr = {"Authorization": f"Bearer {lr.json().get('access_token','')}"}

# 1) PIN = primer nombre, contra P097 finalizado -> PIN acepta, estado bloquea (no escribe)
b1 = {"apostador_id":APOSTADOR_ID, "pin":primer,
      "apuestas":[{"numero_fifa":97,"pred_local":1,"pred_visitante":1}]}
r1 = requests.post(f"{API}/bets/live-guardar-apuestas/2", headers=hdr, json=b1, timeout=60).json()

# 2) PIN = username (ya NO debe valer) contra P104 programado -> rechazo por PIN
b2 = {"apostador_id":APOSTADOR_ID, "pin":username,
      "apuestas":[{"numero_fifa":104,"pred_local":1,"pred_visitante":0}]}
r2 = requests.post(f"{API}/bets/live-guardar-apuestas/2", headers=hdr, json=b2, timeout=60).json()

ok1 = (r1.get("guardadas")==0 and r1.get("resultados") and r1["resultados"][0].get("ok") is False)
ok2 = (r2.get("ok") is False and "PIN" in (r2.get("error") or ""))
ver = "PASS" if (ok1 and ok2) else "REVISAR"
out = (f"id={APOSTADOR_ID} username={username!r} nombre={nombre!r} primer={primer!r}\n"
       f"[1] pin=primer_nombre + P097 finalizado -> {r1}\n"
       f"[2] pin=username + P104 programado (debe rechazar) -> {r2}\n"
       f"RESULTADO: {ver} (primer_nombre_acepta={ok1}, username_rechazado={ok2})\n")
print("\n"+out)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"test_live_guardar_out.txt"),"w",encoding="utf-8").write(out)
