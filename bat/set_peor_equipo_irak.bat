@echo off
echo === Grabando Iraq como peor equipo ===
echo.

REM 1. Buscar ID de Iraq en BD
echo Buscando ID de Iraq...
for /f "usebackq tokens=1" %%i in (`docker exec core-postgres psql -U app_user -d becbuc -t -c "SELECT id FROM equipo WHERE LOWER(nombre) LIKE '%%iraq%%' OR LOWER(nombre_es) LIKE '%%irak%%' OR LOWER(nombre_es) LIKE '%%iraq%%' LIMIT 1;"`) do set IRAK_ID=%%i

set IRAK_ID=%IRAK_ID: =%

if "%IRAK_ID%"=="" (
    echo ERROR: No se encontro Iraq. Equipos disponibles con I:
    docker exec core-postgres psql -U app_user -d becbuc -c "SELECT id, nombre, nombre_es FROM equipo WHERE nombre ILIKE 'I%%' ORDER BY nombre LIMIT 20;"
    pause
    exit /b 1
)
echo Iraq encontrado - ID: %IRAK_ID%

REM 2. Login
echo.
echo Autenticando...
for /f "usebackq delims=" %%t in (`curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"jose\",\"password\":\"catalina\"}" ^| python -c "import sys,json; print(json.load(sys.stdin).get('access_token','ERROR'))"`) do set TOKEN=%%t

if "%TOKEN%"=="ERROR" (
    echo ERROR al hacer login
    pause
    exit /b 1
)
echo Token OK

REM 3. Grabar peor equipo = Iraq
echo.
echo Grabando resultado_peor_equipo_id = %IRAK_ID%...
curl -s -X POST "http://localhost:8000/api/v1/bets/resultados-globales/2" ^
  -H "Authorization: Bearer %TOKEN%" ^
  -H "Content-Type: application/json" ^
  -d "{\"resultado_peor_equipo_id\": %IRAK_ID%}"

echo.

REM 4. Recalcular puntajes
echo Recalculando puntajes...
curl -s -X POST "http://localhost:8000/api/v1/bets/calcular-puntajes/2" ^
  -H "Authorization: Bearer %TOKEN%"

echo.
echo === Listo! Iraq grabado como peor equipo y puntajes recalculados ===
pause
