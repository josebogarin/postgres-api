@echo off
echo === ID de cherem en app_db ===
docker exec core-postgres psql -U app_user -d app_db -t -A -c "SELECT id FROM users WHERE username='cherem';" > "C:\proyecto FAST API\cherem_bd.txt" 2>&1

echo === Apuestas cherem en becbuc (partidos de grupos) ===
docker exec core-postgres psql -U app_user -d becbuc -t -A -F"|" -c "SELECT p.numero_fifa, p.goles_local AS real_gl, p.goles_visitante AS real_gv, a.pred_local AS pred_gl, a.pred_visitante AS pred_gv, COALESCE(pd.pts_resultado,0) AS pts_H, COALESCE(pd.pts_marcador,0) AS pts_I FROM apuesta a JOIN partido p ON p.id = a.partido_id JOIN fase f ON f.id = p.fase_id LEFT JOIN puntaje_detalle pd ON pd.partido_id = p.id AND pd.apostador_id = a.apostador_id WHERE a.apostador_id = (SELECT id FROM dblink('dbname=app_db user=app_user', 'SELECT id FROM users WHERE username=''cherem''') AS t(id INT)) AND f.torneo_id = 2 AND f.tipo ILIKE 'grupo%%' AND p.estado='finalizado' ORDER BY p.numero_fifa;" >> "C:\proyecto FAST API\cherem_bd.txt" 2>&1

type "C:\proyecto FAST API\cherem_bd.txt"
pause
