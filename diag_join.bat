@echo off
echo === Diagnostico join pronosticos_aux vs BD === > "C:\proyecto FAST API\diag_join.txt"

echo Total filas pronosticos_aux: >> "C:\proyecto FAST API\diag_join.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*), COUNT(DISTINCT nombre) AS apostadores, COUNT(DISTINCT numero_partido_fifa) AS partidos FROM pronosticos_aux;" >> "C:\proyecto FAST API\diag_join.txt" 2>&1

echo. >> "C:\proyecto FAST API\diag_join.txt"
echo Nombres en pronosticos_aux vs app_db (muestra): >> "C:\proyecto FAST API\diag_join.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT DISTINCT pa.nombre AS paux_nombre, u.nombre AS db_nombre FROM pronosticos_aux pa JOIN dblink('dbname=app_db user=app_user', 'SELECT id, nombre FROM users') AS u(uid INT, nombre TEXT) ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre)) LIMIT 5;" >> "C:\proyecto FAST API\diag_join.txt" 2>&1

echo. >> "C:\proyecto FAST API\diag_join.txt"
echo Filas del join completo (partidos finalizados grupos): >> "C:\proyecto FAST API\diag_join.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) AS filas_join FROM pronosticos_aux pa JOIN partido p ON p.numero_fifa = pa.numero_partido_fifa JOIN apuesta a ON a.partido_id = p.id JOIN fase f ON f.id = p.fase_id JOIN dblink('dbname=app_db user=app_user', 'SELECT id, nombre FROM users') AS u(uid INT, nombre TEXT) ON LOWER(TRIM(pa.nombre)) = LOWER(TRIM(u.nombre)) AND a.apostador_id = u.uid WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%%' AND p.estado = 'finalizado';" >> "C:\proyecto FAST API\diag_join.txt" 2>&1

type "C:\proyecto FAST API\diag_join.txt"
pause
