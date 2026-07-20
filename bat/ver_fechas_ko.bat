@echo off
echo ================================================
echo  Fechas primeros 4 partidos KO en BD
echo ================================================
docker exec core-postgres psql -U app_user -d becbuc -c ^
"SELECT p.numero_fifa, p.fecha, p.estado, COALESCE(el.nombre_es, el.nombre, 'TBD') AS local, COALESCE(ev.nombre_es, ev.nombre, 'TBD') AS visitante FROM partido p JOIN fase f ON f.id = p.fase_id LEFT JOIN equipo el ON el.id = p.equipo_local_id LEFT JOIN equipo ev ON ev.id = p.equipo_visitante_id WHERE f.tipo <> 'grupo' ORDER BY p.numero_fifa LIMIT 4;"
echo.
pause
