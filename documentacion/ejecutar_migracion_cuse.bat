@echo off
REM ============================================================================
REM SCRIPT: Ejecutar migración CUSE ITAIPÚ CON CÁLCULOS
REM ============================================================================

echo.
echo ============================================================================
echo EJECUTANDO MIGRACIÓN CUSE ITAIPÚ (2015-2026)
echo ============================================================================
echo.

REM Ejecutar SQL
echo [1] Creando tabla y cargando datos...
Get-Content "C:\Proyectos\Energia\documentacion\cuse_con_calculos_2015_2026.sql" | docker exec -i core-postgres psql -U app_user -d energia

echo.
echo ============================================================================
echo VERIFICANDO DATOS IMPORTADOS
echo ============================================================================
echo.

REM Verificar tabla creada
echo [2] Verificando estructura de la tabla...
docker exec core-postgres psql -U app_user -d energia -c "\d cuse_itaipu_con_calculos" | head -20

echo.
echo [3] Contando filas importadas...
docker exec core-postgres psql -U app_user -d energia -c "SELECT COUNT(*) as total_filas FROM cuse_itaipu_con_calculos;"

echo.
echo [4] Mostrando últimos 5 años (2020-2024)...
docker exec core-postgres psql -U app_user -d energia -c "SELECT anio, tarifa_cuse_usd_kw_mes, ROUND(gastos_totales_usd_m::numeric, 1) as gastos, ROUND(gasto_social_usd_m::numeric, 1) as soc FROM cuse_itaipu_con_calculos WHERE anio >= 2020 ORDER BY anio DESC;"

echo.
echo ============================================================================
echo ✅ Migración completada exitosamente
echo ============================================================================
echo.
echo Endpoints disponibles:
echo   GET  /api/v1/simulador/cuse-por-ano?anno=2024
echo   GET  /api/v1/simulador/cuse-por-ano (todos)
echo   POST /api/v1/simulador/cuse-guardar (años 2027+)
echo.
pause
