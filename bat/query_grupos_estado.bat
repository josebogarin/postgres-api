@echo off
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT COUNT(*) total, SUM(CASE WHEN p.estado='finalizado' THEN 1 ELSE 0 END) finalizados, SUM(CASE WHEN COALESCE(p.datos_confirmados,FALSE)=TRUE THEN 1 ELSE 0 END) confirmados, SUM(CASE WHEN p.api_fixture_id IS NOT NULL THEN 1 ELSE 0 END) sincronizados, SUM(CASE WHEN p.amarillas IS NOT NULL THEN 1 ELSE 0 END) con_amarillas, SUM(CASE WHEN p.decisiones_var IS NOT NULL THEN 1 ELSE 0 END) con_var FROM partido p JOIN fase f ON f.id = p.fase_id WHERE f.torneo_id = 2 AND f.tipo ILIKE 'grupo%%';" > "%~dp0..\grupos_estado.txt" 2>&1
echo.
echo === RESULTADO ===
type "%~dp0..\grupos_estado.txt"
echo.
echo === DETALLE POR ESTADO ===
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT p.estado, COUNT(*) cant FROM partido p JOIN fase f ON f.id=p.fase_id WHERE f.torneo_id=2 AND f.tipo ILIKE 'grupo%%' GROUP BY p.estado ORDER BY cant DESC;" >> "%~dp0..\grupos_estado.txt" 2>&1
type "%~dp0..\grupos_estado.txt"
pause
