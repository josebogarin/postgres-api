@echo off
set OUTPUTS=C:\Users\Jose Bogarin\AppData\Roaming\Claude\local-agent-mode-sessions\a9fdc79d-9227-450c-a0c1-27eafc601471\dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\agent\local_ditto_dfc0381f-d9d1-4349-b3fa-24cab5c5da8b\outputs
set LOG=%OUTPUTS%\check_estado_log.txt

docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) FILTER (WHERE p.estado='finalizado') AS finalizados, COUNT(*) FILTER (WHERE p.estado='en_juego') AS en_juego, COUNT(*) FILTER (WHERE p.estado='programado') AS programados, COUNT(*) AS total FROM partido p JOIN fase f ON f.id = p.fase_id WHERE f.torneo_id = 2;" > "%LOG%" 2>&1

docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(DISTINCT partido_id) AS partidos_calculados, COUNT(DISTINCT apostador_id) AS apostadores_calculados FROM puntaje_detalle WHERE torneo_id = 2;" >> "%LOG%" 2>&1

docker exec core-postgres psql -U app_user -d becbuc -c "SELECT a.nombre_apostador, SUM(pd.pts_resultado + pd.pts_marcador + pd.pts_amarillas + pd.pts_rojas + pd.pts_var + COALESCE(pd.pts_penales_partido,0) + pd.pts_minuto + pd.pts_penales_tanda) AS total FROM puntaje_detalle pd JOIN (SELECT DISTINCT apostador_id, nombre_apostador FROM apuesta WHERE nombre_apostador IS NOT NULL) a ON a.apostador_id = pd.apostador_id WHERE pd.torneo_id = 2 GROUP BY a.nombre_apostador ORDER BY total DESC LIMIT 10;" >> "%LOG%" 2>&1

docker exec core-postgres psql -U app_user -d becbuc -c "SELECT created_at, contexto, ok FROM api_sync_log ORDER BY created_at DESC LIMIT 5;" >> "%LOG%" 2>&1
