@echo off
echo === Real vs predicciones cherem (10 partidos) === > "%~dp0..\real2.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT p.numero_fifa, p.goles_local AS rl, p.goles_visitante AS rv, a.pred_local AS pl, a.pred_visitante AS pv, COALESCE(pd.pts_resultado,0) AS H_old, COALESCE(pd.pts_marcador,0) AS I_old FROM apuesta a JOIN partido p ON p.id=a.partido_id LEFT JOIN puntaje_detalle pd ON pd.partido_id=p.id AND pd.apostador_id=a.apostador_id WHERE a.apostador_id=15 AND p.numero_fifa IN (37,38,49,50,55,56,61,62,65,66) ORDER BY p.numero_fifa;" >> "%~dp0..\real2.txt" 2>&1
type "%~dp0..\real2.txt"
pause
