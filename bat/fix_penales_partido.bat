@echo off
echo === Fix penales_partido para partidos con tanda ===
echo.
echo PASO 1: Ver estado actual de partidos con tanda:
echo.
Get-Content "C:\proyecto FAST API\documentacion\fix_penales_partido_tanda.sql" | docker exec -i core-postgres psql -U app_user -d becbuc
echo.
echo PASO 2: Para corregir un partido específico, ejecutar:
echo docker exec core-postgres psql -U app_user -d becbuc -c "UPDATE partido SET penales_partido = 0, datos_confirmados = FALSE WHERE numero_fifa = N;"
echo.
echo PASO 3: Luego hacer Sync desde API-Football en Herramientas (recalculará el valor correcto)
echo.
pause
