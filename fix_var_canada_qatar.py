"""
Fix rapido: setea decisiones_var=2 para Canada vs Qatar y recalcula puntajes.
Correr desde: cd "C:\proyecto FAST API\backend" && python ..\fix_var_canada_qatar.py
"""
import subprocess, sys, json, urllib.request

# 1. UPDATE via psql
cmd = [
    "docker", "exec", "core-postgres", "psql",
    "-U", "app_user", "-d", "becbuc",
    "-c",
    "UPDATE partido SET decisiones_var = 2 "
    "WHERE id IN ("
    "  SELECT p.id FROM partido p "
    "  JOIN equipo el ON el.id=p.equipo_local_id "
    "  JOIN equipo ev ON ev.id=p.equipo_visitante_id "
    "  WHERE (el.nombre ILIKE '%canada%' AND ev.nombre ILIKE '%qatar%') "
    "     OR (el.nombre ILIKE '%qatar%'  AND ev.nombre ILIKE '%canada%')"
    ") RETURNING id, decisiones_var;"
]
print("=== Actualizando BD ===")
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stdout or r.stderr)

# 2. Recalcular puntajes via API
print("=== Recalculando puntajes ===")
try:
    # Login
    login_data = json.dumps({"username": "jose", "password": "catalina"}).encode()
    req = urllib.request.Request(
        "http://localhost:8000/api/v1/auth/login",
        data=login_data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token = json.loads(resp.read())["access_token"]

    # Calcular puntajes
    req2 = urllib.request.Request(
        "http://localhost:8000/api/v1/bets/calcular-puntajes/2",
        data=b"", headers={"Authorization": f"Bearer {token}"}, method="POST"
    )
    with urllib.request.urlopen(req2, timeout=30) as resp2:
        result = json.loads(resp2.read())
    print(f"Puntajes OK: plenos={result.get('plenos')} aciertos={result.get('aciertos')}")
except Exception as e:
    print(f"API error (recalcular manualmente): {e}")

print("=== Listo ===")
