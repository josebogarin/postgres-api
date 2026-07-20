"""
Actualiza la hora del partido Mexico vs Inglaterra en la BD.
22:00 PYT (Paraguay, julio = UTC-4) => 2026-07-06 02:00:00 UTC
"""
import subprocess, sys

def psql(sql):
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", "becbuc", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print("STDERR:", r.stderr)
    return r.returncode

print("=== BUSCANDO partido Mexico vs Inglaterra ===")
psql("""
SELECT p.id, p.numero_fifa, p.fecha, p.estado,
       el.nombre AS local, ev.nombre AS visitante
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE (el.nombre ILIKE '%mexico%' OR el.nombre_es ILIKE '%mexico%' OR el.nombre ILIKE '%m%xico%')
   OR (ev.nombre ILIKE '%england%' OR ev.nombre_es ILIKE '%inglat%')
ORDER BY p.numero_fifa;
""")

print()
print("=== APLICANDO UPDATE: nueva hora 2026-07-06 02:00:00 UTC (= 22:00 PYT) ===")
rc = psql("""
UPDATE partido
SET    fecha = '2026-07-06 02:00:00'
WHERE  equipo_local_id IN (
           SELECT id FROM equipo
           WHERE nombre ILIKE '%mexico%' OR nombre_es ILIKE '%mexico%' OR nombre ILIKE '%m%xico%'
       )
   OR  equipo_visitante_id IN (
           SELECT id FROM equipo
           WHERE nombre ILIKE '%england%' OR nombre_es ILIKE '%inglat%'
       );
""")
if rc != 0:
    sys.exit(1)

print()
print("=== VERIFICACION POST-UPDATE ===")
psql("""
SELECT p.id, p.numero_fifa,
       p.fecha AS fecha_utc,
       p.fecha AT TIME ZONE 'America/Asuncion' AS hora_paraguay,
       p.estado,
       el.nombre AS local, ev.nombre AS visitante
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE (el.nombre ILIKE '%mexico%' OR el.nombre_es ILIKE '%mexico%' OR el.nombre ILIKE '%m%xico%')
   OR (ev.nombre ILIKE '%england%' OR ev.nombre_es ILIKE '%inglat%')
ORDER BY p.numero_fifa;
""")

print()
print("=== LISTO ===")
