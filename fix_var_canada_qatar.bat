@echo off
echo === Fix VAR Canada vs Qatar (decisiones_var = 2) ===
echo.

echo Buscando partido Canada vs Qatar...
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT p.id, el.nombre AS local, ev.nombre AS visitante, p.decisiones_var, p.amarillas, p.rojas FROM partido p JOIN equipo el ON el.id=p.equipo_local_id JOIN equipo ev ON ev.id=p.equipo_visitante_id WHERE (el.nombre ILIKE '%%canada%%' AND ev.nombre ILIKE '%%qatar%%') OR (el.nombre ILIKE '%%qatar%%' AND ev.nombre ILIKE '%%canada%%');"

echo.
echo Aplicando fix decisiones_var = 2...
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE partido SET decisiones_var = 2 WHERE id IN (SELECT p.id FROM partido p JOIN equipo el ON el.id=p.equipo_local_id JOIN equipo ev ON ev.id=p.equipo_visitante_id WHERE (el.nombre ILIKE '%%canada%%' AND ev.nombre ILIKE '%%qatar%%') OR (el.nombre ILIKE '%%qatar%%' AND ev.nombre ILIKE '%%canada%%')) RETURNING id, decisiones_var;"

echo.
echo Recalculando puntajes via API...
powershell -Command "$login = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -ContentType 'application/json' -Body '{\"username\":\"jose\",\"password\":\"catalina\"}'; $tok = $login.access_token; $r = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/bets/calcular-puntajes/2' -Method POST -Headers @{Authorization=\"Bearer $tok\"}; Write-Host ('Puntajes OK: plenos=' + $r.plenos + ' aciertos=' + $r.aciertos)"

echo.
echo Listo!
pause
