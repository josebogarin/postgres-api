@echo off
echo Exportando puntajes BECBUC...
docker exec core-postgres psql -U app_user -d becbuc -t -A -F "|" -c "SELECT COALESCE(a.nombre_apostador, pd.apostador_id::text) AS alias, COALESCE(SUM(pd.pts_resultado),0)::INT AS H, COALESCE(SUM(pd.pts_marcador),0)::INT AS I, COALESCE(SUM(pd.pts_amarillas),0)::INT AS J, COALESCE(SUM(pd.pts_rojas),0)::INT AS K, COALESCE(SUM(pd.pts_var),0)::INT AS L, COALESCE(SUM(pd.pts_penales_partido),0)::INT AS M, COALESCE(SUM(pd.pts_minuto),0)::INT AS N, COALESCE(SUM(pd.pts_penales_tanda),0)::INT AS O, COALESCE(SUM(pd.pts_resultado+pd.pts_marcador+pd.pts_amarillas+pd.pts_rojas+pd.pts_var+pd.pts_penales_partido+pd.pts_minuto+pd.pts_penales_tanda),0)::INT AS total FROM puntaje_detalle pd LEFT JOIN (SELECT DISTINCT ON (apostador_id) apostador_id, nombre_apostador FROM apuesta WHERE torneo_id=2 AND nombre_apostador IS NOT NULL) a ON pd.apostador_id = a.apostador_id WHERE pd.torneo_id = 2 GROUP BY alias ORDER BY total DESC;" > "%~dp0..\becbuc_scores.csv" 2>&1
echo.
echo Archivo guardado en: %~dp0..\becbuc_scores.csv
pause
