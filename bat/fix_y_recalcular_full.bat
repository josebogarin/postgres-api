@echo off
echo ============================================
echo   BECBUC - Fix VAR + Recalculo completo
echo ============================================
echo.

REM 1. Corregir Canada vs Qatar (decisiones_var=2)
echo [1/3] Corrigiendo Canada vs Qatar VAR=2...
docker exec core-postgres psql -U app_user -d becbuc -c ^
  "UPDATE partido SET decisiones_var=2 WHERE id=(SELECT p.id FROM partido p JOIN equipo el ON el.id=p.equipo_local_id JOIN equipo ev ON ev.id=p.equipo_visitante_id WHERE (LOWER(el.nombre) LIKE '%%canad%%' AND LOWER(ev.nombre) LIKE '%%qatar%%') OR (LOWER(ev.nombre) LIKE '%%canad%%' AND LOWER(el.nombre) LIKE '%%qatar%%') LIMIT 1);"
if errorlevel 1 (
  echo ERROR en update Canada-Qatar. Continuando igual...
)

REM 2. Recalcular puntajes via API
echo.
echo [2/3] Recalculando puntajes (esto puede tardar)...
curl -s -X POST http://localhost:8000/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"jose\",\"password\":\"catalina\"}" ^
  -o _tok_temp.json

for /f "tokens=2 delims=:, " %%a in ('findstr /i "access_token" _tok_temp.json') do (
  set TOKEN=%%~a
  set TOKEN=!TOKEN:"=!
)

setlocal EnableDelayedExpansion
for /f "usebackq tokens=*" %%t in (`powershell -NoProfile -Command "(Get-Content _tok_temp.json | ConvertFrom-Json).access_token"`) do set TOKEN=%%t

echo Token obtenido. Llamando calcular-puntajes...
curl -s -X POST "http://localhost:8000/api/v1/bets/calcular-puntajes/2" ^
  -H "Authorization: Bearer !TOKEN!" ^
  -H "Content-Type: application/json"

echo.
echo [3/3] Verificando top5 ranking...
curl -s "http://localhost:8000/api/v1/bets/ranking/2" ^
  -H "Authorization: Bearer !TOKEN!" | powershell -NoProfile -Command ^
  "$data = $Input | ConvertFrom-Json; $data | Select-Object -First 5 | Format-Table nombre,puntos_total,cat_var,cat_amarillas -AutoSize"

del _tok_temp.json 2>nul
echo.
echo ============================================
echo   LISTO - Recarga becbuc-live.html
echo ============================================
pause
