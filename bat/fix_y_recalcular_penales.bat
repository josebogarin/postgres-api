@echo off
echo ============================================================
echo  BECBUC - Fix penales_partido + Recalcular puntajes
echo ============================================================
echo.

echo [1/3] Corrigiendo penales_partido en BD...
docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE partido SET penales_partido = 0, datos_confirmados = FALSE WHERE penales_local IS NOT NULL AND penales_partido IS NOT NULL AND penales_partido = (COALESCE(penales_local,0) + COALESCE(penales_visitante,0));"

echo.
echo [2/3] Estado post-fix:
docker exec core-postgres psql -U app_user -d becbuc -c "SELECT numero_fifa, penales_local, penales_visitante, penales_partido FROM partido WHERE penales_local IS NOT NULL ORDER BY numero_fifa;"

echo.
echo [3/3] Recalculando puntajes via API...
for /f "tokens=*" %%i in ('curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"jose\",\"password\":\"catalina\"}" ^| python -c "import sys,json; print(json.load(sys.stdin)[\"access_token\"])"') do set TOKEN=%%i

curl -s -X POST "http://localhost:8000/api/v1/bets/calcular-puntajes/2" -H "Authorization: Bearer %TOKEN%" -H "Content-Type: application/json"

echo.
echo ============================================================
echo  Listo. Verificar puntajes en el portal.
echo ============================================================
pause
