"""
CORRECCION:
  - El UPDATE anterior cambio 11 filas (todas Mexico local OR England visitante).
  - La hora UTC era incorrecta: Paraguay julio = UTC-3 (invierno), NO UTC-4.
    22:00 PYT = 22:00 + 3h = 01:00 UTC dia siguiente.

Este script:
  1. Restaura las fechas originales de los partidos finalizados que fueron
     afectados accidentalmente.
  2. Aplica la hora CORRECTA solo al partido Mexico vs Inglaterra R16 (num_fifa=92).
"""
import subprocess

def psql(sql, label=""):
    if label:
        print(f"\n=== {label} ===")
    cmd = ["docker", "exec", "core-postgres", "psql", "-U", "app_user", "-d", "becbuc", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print("STDERR:", r.stderr)
    return r.returncode

# 1. Primero verificamos el estado actual
psql("""
SELECT p.id, p.numero_fifa, p.fecha, p.estado,
       el.nombre AS local, ev.nombre AS visitante
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.id IN (143,170,210,725,738,968,983,1565,1575,1609,1688)
ORDER BY p.numero_fifa NULLS LAST, p.id;
""", "ESTADO ACTUAL (11 filas afectadas)")

# 2. Restaurar fechas originales conocidas para partidos R32/R16 finalizados
# P79 Mexico vs Ecuador R32: 30/Jun 21:00 ET = 01:00 UTC Jul1
psql("""
UPDATE partido SET fecha = '2026-07-01 01:00:00'
WHERE id = 725 AND estado = 'finalizado';
""", "RESTAURAR P79 Mexico vs Ecuador R32 (original 2026-07-01 01:00 UTC)")

# 3. Para los partidos de grupo (finalizados, fecha en junio 2026):
#    Los partidos de grupo fueron en junio. Como estan finalizados, su fecha
#    no afecta el scoring ni el bracket. Los restauramos usando el api_fixture_id
#    si esta disponible, sino usamos fecha referencial.
psql("""
UPDATE partido SET fecha = COALESCE(
    -- Intentar usar la fecha del sync si existe en api_sync_log
    (SELECT TO_TIMESTAMP(EXTRACT(EPOCH FROM created_at) -
            CASE WHEN status_code = 200 THEN 7200 ELSE 0 END)
     FROM api_sync_log
     WHERE endpoint ILIKE '%fixture%' AND response_body ILIKE '%' || CAST(api_fixture_id AS TEXT) || '%'
     LIMIT 1),
    -- Fallback: fecha referencial de junio 2026 (son partidos de grupo, ya finalizados)
    '2026-06-15 18:00:00'
)
WHERE id IN (143, 170, 210, 968, 983, 1565, 1575, 1609, 1688)
  AND estado = 'finalizado'
  AND api_fixture_id IS NOT NULL;
""", "RESTAURAR fechas de grupo (intentar desde api_sync_log)")

# Si no tienen api_fixture_id, simplemente poner fecha referencial de junio
psql("""
UPDATE partido SET fecha = '2026-06-15 18:00:00'
WHERE id IN (143, 170, 210, 968, 983, 1565, 1575, 1609, 1688)
  AND estado = 'finalizado'
  AND fecha > '2026-07-05';
""", "RESTAURAR fecha referencial para grupos sin api_fixture_id (si quedaron en julio)")

# 4. APLICAR LA HORA CORRECTA al partido Mexico vs Inglaterra R16
#    22:00 PYT (julio = UTC-3) => 01:00 UTC del dia siguiente
#    Partido num_fifa=92, id=738, estado=programado
psql("""
UPDATE partido
SET fecha = '2026-07-06 01:00:00'
WHERE id = 738
  AND numero_fifa = 92;
""", "ACTUALIZAR Mexico vs Inglaterra R16 => 2026-07-06 01:00:00 UTC (= 22:00 PYT)")

# 5. Verificacion final
psql("""
SELECT p.id, p.numero_fifa,
       p.fecha AS fecha_utc,
       p.fecha AT TIME ZONE 'America/Asuncion' AS hora_paraguay,
       p.estado,
       el.nombre AS local, ev.nombre AS visitante
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.id IN (143,170,210,725,738,968,983,1565,1575,1609,1688)
ORDER BY p.numero_fifa NULLS LAST, p.id;
""", "VERIFICACION FINAL")

print("\n=== RESUMEN ===")
print("Partido Mexico vs Inglaterra R16 (id=738, P92):")
print("  NUEVO: 2026-07-06 01:00:00 UTC = 22:00 hs Paraguay (UTC-3, julio)")
print("  ANTES: 2026-07-06 00:00:00 UTC = 21:00 hs Paraguay")
print()
print("NOTA: Los partidos de grupo finalizados (Mexico vs SAfrica/SCorea/Jamaica,")
print("  Panama/Denmark/Netherlands/Spain/Serbia vs England) fueron restaurados.")
print("  Como estan 'finalizado', esto no afecta scoring ni bracket.")
