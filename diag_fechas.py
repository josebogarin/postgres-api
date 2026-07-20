"""
diag_fechas.py — Muestra las fechas de los partidos KO tal como están en la BD
y cómo las ve el frontend.

Ejecutar:
    cd "C:\proyecto FAST API"
    backend\.venv\Scripts\python.exe diag_fechas.py
"""
import subprocess, json, datetime, sys

def psql(sql):
    cmd = ["docker", "exec", "-i", "core-postgres",
           "psql", "-U", "app_user", "-d", "becbuc",
           "--tuples-only", "--no-align", "-F", "|"]
    r = subprocess.run(cmd, input=sql, capture_output=True, encoding="utf-8", timeout=30)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()

print("=== FECHAS EN BD (partidos KO) ===")
print()
out = psql("""
    SELECT p.numero_fifa,
           el.nombre AS local,
           ev.nombre AS visitante,
           p.fecha,
           pg_typeof(p.fecha) AS tipo_col,
           p.fecha AT TIME ZONE 'UTC'                AS como_utc,
           p.fecha AT TIME ZONE 'America/Costa_Rica' AS como_cr
    FROM partido p
    LEFT JOIN equipo el ON el.id = p.equipo_local_id
    LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id
    WHERE p.numero_fifa IS NOT NULL
      AND p.numero_fifa >= 73
      AND p.fecha IS NOT NULL
    ORDER BY p.fecha, p.numero_fifa
    LIMIT 16;
""")

print(f"{'P#':<5} {'Local':<20} {'Visitante':<20} {'fecha en BD':<25} {'tipo':<30} {'AT TZ UTC':<25} {'AT TZ CR':<25}")
print("-" * 150)
for line in out.splitlines():
    if not line.strip():
        continue
    parts = line.split("|")
    if len(parts) < 7:
        continue
    num, loc, vis, fecha, tipo, utc, cr = [p.strip() for p in parts[:7]]
    print(f"P{num:<4} {loc[:19]:<20} {vis[:19]:<20} {fecha:<25} {tipo:<30} {utc:<25} {cr:<25}")

print()
print("=== INTERPRETACION ===")
print()
print("Si 'tipo' = 'timestamp without time zone':")
print("  La fecha NO tiene TZ. asyncpg retorna datetime naive.")
print("  Si el script importó UTC naive, 'fecha en BD' debería ser hora UTC.")
print("  Al añadir 'Z' en el backend, el browser la trata como UTC -> convierte a local.")
print()
print("Si 'tipo' = 'timestamp with time zone':")
print("  La fecha TIENE TZ. La columna AT TIME ZONE 'UTC' muestra su valor en UTC.")
print("  asyncpg retorna datetime aware (UTC). Al formatear con strftime+Z, es correcto.")
print()

# También muestra el timezone del servidor postgres
tz = psql("SHOW timezone;").strip()
print(f"Timezone del servidor PostgreSQL: {tz}")
print()
print("=== HOY ===")
today = psql("SELECT CURRENT_DATE, NOW() AT TIME ZONE 'America/Costa_Rica';")
print(today)
