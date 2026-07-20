"""
Diagnostico: muestra los partidos con tanda y su penales_partido actual.
Ejecutar con el servidor activo para ver si el valor esta mal.

python diagnosticar_penales_partido.py
"""
import httpx, sys, json

BASE = "http://localhost:8000"

# Login
r = httpx.post(f"{BASE}/api/v1/auth/login",
               json={"username": "jose", "password": "catalina"})
if r.status_code != 200:
    print("❌ Login failed:", r.text); sys.exit(1)
tok = r.json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# Buscar partidos con tanda
r = httpx.get(f"{BASE}/api/v1/admin/db-tables/partido/rows",
              headers=H, params={"limit": 200}, timeout=30)
if r.status_code != 200:
    print("Error:", r.text); sys.exit(1)

rows = r.json().get("rows", [])
print(f"\n{'#FIFA':<6} {'Local':<20} {'Res':<6} {'Visitante':<20} {'TandaL':<7} {'TandaV':<7} {'PenPartido(M)':<14} {'Confirmado'}")
print("-" * 100)
for row in rows:
    if row.get("penales_local") is not None:
        pp = row.get("penales_partido") or 0
        tl = row.get("penales_local") or 0
        tv = row.get("penales_visitante") or 0
        flag = "⚠️ SOSPECHOSO" if pp > 2 else "✅"
        print(f"{str(row.get('numero_fifa','?')):<6} "
              f"{str(row.get('nombre_local','?'))[:19]:<20} "
              f"{row.get('goles_local','?')}-{row.get('goles_visitante','?'):<4} "
              f"{str(row.get('nombre_visitante','?'))[:19]:<20} "
              f"{tl:<7} {tv:<7} {pp:<14} "
              f"{'Sí' if row.get('datos_confirmados') else 'No'} {flag}")
