# DIAGNÓSTICO CHEREM - Ejecutar en PowerShell desde C:\proyecto FAST API
# Copia y pega este bloque completo en la terminal

Write-Host "=== 1. Partido #8 (grupo) en becbuc ===" -ForegroundColor Cyan
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT ROW_NUMBER() OVER (ORDER BY f.orden, p.id)::int AS num_seq,
       p.id, COALESCE(el.nombre,'TBD') AS local,
       p.goles_local, p.goles_visitante,
       COALESCE(ev.nombre,'TBD') AS visitante, p.estado
FROM partido p JOIN fase f ON f.id=p.fase_id
LEFT JOIN equipo el ON el.id=p.equipo_local_id
LEFT JOIN equipo ev ON ev.id=p.equipo_visitante_id
WHERE p.torneo_id=2 AND f.tipo='grupo'
ORDER BY f.orden, p.id LIMIT 10;"

Write-Host "`n=== 2. Apuestas en el partido #8 ===" -ForegroundColor Cyan
docker exec core-postgres psql -U app_user -d becbuc -c "
SELECT ap.apostador_id, ap.pred_local, ap.pred_visitante, ap.puntos
FROM apuesta ap
WHERE ap.partido_id = (
    SELECT id FROM (
        SELECT p.id, ROW_NUMBER() OVER (ORDER BY f.orden, p.id) as rn
        FROM partido p JOIN fase f ON f.id=p.fase_id
        WHERE p.torneo_id=2 AND f.tipo='grupo'
    ) sub WHERE rn=8
) ORDER BY ap.apostador_id;"

Write-Host "`n=== 3. Usuarios en app_db con 'cherem' en username/nombre ===" -ForegroundColor Cyan
docker exec core-postgres psql -U app_user -d app_db -c "
SELECT id, username, nombre, email
FROM users
WHERE username ILIKE '%cherem%' OR nombre ILIKE '%cherem%'
   OR username ILIKE '%andres%bogarin%' OR nombre ILIKE '%andres%bogarin%'
ORDER BY id;"

Write-Host "`n=== 4. Todos los usernames en app_db (para identificar cherem) ===" -ForegroundColor Cyan
docker exec core-postgres psql -U app_user -d app_db -c "
SELECT id, username, nombre FROM users ORDER BY username LIMIT 50;"
