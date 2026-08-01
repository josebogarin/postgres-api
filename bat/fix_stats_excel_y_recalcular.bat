@echo off
echo =====================================================
echo FIX PARTIDO STATS FROM EXCEL + RECALCULAR PUNTAJES
echo =====================================================
echo.

echo [1/3] Aplicando fix_partido_stats_from_excel.sql en Docker...
Get-Content "%~dp0..\documentacion\fix_partido_stats_from_excel.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
if %errorlevel% neq 0 (
    echo ERROR al ejecutar SQL en Docker. Verifica que Docker este corriendo.
    pause
    exit /b 1
)
echo OK - SQL ejecutado correctamente.
echo.

echo [2/3] Obteniendo token de autenticacion...
for /f "delims=" %%i in ('powershell -Command "(Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/auth/login' -Method POST -ContentType 'application/json' -Body '{\"username\":\"jose\",\"password\":\"catalina\"}').access_token"') do set TOKEN=%%i
if "%TOKEN%"=="" (
    echo ERROR: No se pudo obtener token. Verifica que el servidor uvicorn este corriendo.
    pause
    exit /b 1
)
echo OK - Token obtenido.
echo.

echo [3/3] Recalculando puntajes...
for /f "delims=" %%r in ('powershell -Command "(Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/bets/calcular-puntajes/2' -Method POST -Headers @{Authorization='Bearer %TOKEN%'}) | ConvertTo-Json -Compress"') do set RESULT=%%r
echo Resultado: %RESULT%
echo.

echo =====================================================
echo COMPLETADO. Abre el portal y verifica el ranking.
echo =====================================================
pause
