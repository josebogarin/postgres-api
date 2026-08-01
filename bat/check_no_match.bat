@echo off
echo === Usuarios en app_db con nombres que podrian coincidir ===
docker exec core-postgres psql -U app_user -d app_db -c "SELECT id, username, nombre FROM users ORDER BY nombre;" > "%~dp0..\no_match.txt" 2>&1

echo. >> "%~dp0..\no_match.txt"
echo === nombre_apostador en tabla apuesta (distintos) === >> "%~dp0..\no_match.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT DISTINCT apostador_id, nombre_apostador FROM apuesta ORDER BY nombre_apostador;" >> "%~dp0..\no_match.txt" 2>&1

echo. >> "%~dp0..\no_match.txt"
echo === apostadores en puntaje_detalle vs usuarios en app_db === >> "%~dp0..\no_match.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT pd.apostador_id, COUNT(*) AS partidos, SUM(pd.pts_resultado+pd.pts_marcador) AS pts_HI FROM puntaje_detalle pd WHERE pd.torneo_id=2 GROUP BY pd.apostador_id HAVING pd.apostador_id NOT IN (SELECT id FROM dblink('dbname=app_db user=app_user','SELECT id FROM users') AS t(id INT)) ORDER BY pd.apostador_id;" >> "%~dp0..\no_match.txt" 2>&1

type "%~dp0..\no_match.txt"
pause
