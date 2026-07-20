@echo off
echo Recalculando puntajes... > "C:\proyecto FAST API\recalc_result.txt"
"C:\proyecto FAST API\backend\.venv\Scripts\python.exe" "C:\proyecto FAST API\recalc_puntajes.py" >> "C:\proyecto FAST API\recalc_result.txt" 2>&1
echo. >> "C:\proyecto FAST API\recalc_result.txt"
echo === Puntajes de cherem por partido (grupos) === >> "C:\proyecto FAST API\recalc_result.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT p.numero_fifa, COALESCE(pd.pts_resultado,0) AS H, COALESCE(pd.pts_marcador,0) AS I, COALESCE(pd.pts_amarillas,0) AS J, COALESCE(pd.pts_var,0) AS L, COALESCE(pd.pts_penales_partido,0) AS M, COALESCE(pd.pts_minuto,0) AS N, (COALESCE(pd.pts_resultado,0)+COALESCE(pd.pts_marcador,0)+COALESCE(pd.pts_amarillas,0)+COALESCE(pd.pts_rojas,0)+COALESCE(pd.pts_var,0)+COALESCE(pd.pts_penales_partido,0)+COALESCE(pd.pts_minuto,0)) AS total FROM puntaje_detalle pd JOIN partido p ON p.id=pd.partido_id JOIN fase f ON f.id=p.fase_id WHERE pd.apostador_id=15 AND f.torneo_id=2 AND f.tipo ILIKE 'grupo%%' AND p.estado='finalizado' ORDER BY p.numero_fifa;" >> "C:\proyecto FAST API\recalc_result.txt" 2>&1
echo. >> "C:\proyecto FAST API\recalc_result.txt"
echo === TOTALES de cherem (grupos finalizados) === >> "C:\proyecto FAST API\recalc_result.txt"
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT SUM(COALESCE(pts_resultado,0)) AS H, SUM(COALESCE(pts_marcador,0)) AS I, SUM(COALESCE(pts_amarillas,0)) AS J, SUM(COALESCE(pts_rojas,0)) AS K, SUM(COALESCE(pts_var,0)) AS L, SUM(COALESCE(pts_penales_partido,0)) AS M, SUM(COALESCE(pts_minuto,0)) AS N, SUM(COALESCE(pts_penales_tanda,0)) AS O, SUM(COALESCE(pts_resultado,0)+COALESCE(pts_marcador,0)+COALESCE(pts_amarillas,0)+COALESCE(pts_rojas,0)+COALESCE(pts_var,0)+COALESCE(pts_penales_partido,0)+COALESCE(pts_minuto,0)) AS total_partidos FROM puntaje_detalle pd JOIN partido p ON p.id=pd.partido_id JOIN fase f ON f.id=p.fase_id WHERE pd.apostador_id=15 AND f.torneo_id=2 AND f.tipo ILIKE 'grupo%%' AND p.estado='finalizado';" >> "C:\proyecto FAST API\recalc_result.txt" 2>&1
type "C:\proyecto FAST API\recalc_result.txt"
pause
