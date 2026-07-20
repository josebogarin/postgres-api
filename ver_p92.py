import subprocess
r = subprocess.run(["docker","exec","core-postgres","psql","-U","app_user","-d","becbuc","-c",
"""SELECT p.id, p.numero_fifa, p.fecha AS fecha_utc,
       p.fecha AT TIME ZONE 'America/Asuncion' AS hora_asuncion,
       p.fecha AT TIME ZONE 'America/Mexico_City' AS hora_mexico,
       p.estado, el.nombre AS local, ev.nombre AS visitante
FROM partido p
JOIN equipo el ON el.id = p.equipo_local_id
JOIN equipo ev ON ev.id = p.equipo_visitante_id
WHERE p.numero_fifa = 92;"""],
capture_output=True, text=True)
print(r.stdout or r.stderr)
